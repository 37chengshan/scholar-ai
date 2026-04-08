import { S3Client, PutObjectCommand, GetObjectCommand, DeleteObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { createWriteStream, createReadStream, promises as fsPromises } from 'fs';
import { Readable } from 'stream';
import path from 'path';
import mime from 'mime-types';
import { logger } from '../utils/logger';

// S3 Client configuration
const s3Client = new S3Client({
  endpoint: process.env.OSS_ENDPOINT,
  region: process.env.OSS_REGION || 'oss-cn-beijing',
  credentials: {
    accessKeyId: process.env.OSS_ACCESS_KEY_ID || '',
    secretAccessKey: process.env.OSS_ACCESS_KEY_SECRET || '',
  },
  forcePathStyle: true, // Required for MinIO compatibility
});

const BUCKET_NAME = process.env.OSS_BUCKET || 'scholarai-papers';
const PRESIGNED_URL_EXPIRES = 3600; // 1 hour in seconds

// Local storage path for development (when OSS is not configured)
const LOCAL_STORAGE_PATH = process.env.LOCAL_STORAGE_PATH || './uploads';
// Only use local storage if OSS_ENDPOINT is explicitly set to 'local' or not set at all
const USE_LOCAL_STORAGE = process.env.OSS_ENDPOINT === 'local' || !process.env.OSS_ENDPOINT;

/**
 * Initialize local storage directory
 */
async function ensureLocalStorageDir(): Promise<void> {
  if (!USE_LOCAL_STORAGE) return;
  try {
    await fsPromises.mkdir(LOCAL_STORAGE_PATH, { recursive: true });
  } catch (error) {
    logger.error('Failed to create local storage directory:', error);
  }
}

// Initialize on module load
ensureLocalStorageDir();

/**
 * Generate a storage key for object storage
 * Format: {userId}_{originalFilename}
 */
export function generateStorageKey(userId: string, originalFilename: string): string {
  // Sanitize filename to avoid path traversal and special characters
  const sanitized = originalFilename
    .replace(/[^a-zA-Z0-9.-]/g, '_')
    .replace(/_{2,}/g, '_');
  return `${userId}_${sanitized}`;
}

/**
 * Get local file path for a storage key
 */
function getLocalFilePath(storageKey: string): string {
  // Prevent path traversal
  const safeKey = storageKey.replace(/\.\//g, '').replace(/\.\./g, '');
  return path.join(LOCAL_STORAGE_PATH, safeKey);
}

/**
 * Generate a presigned URL for direct upload to object storage
 * In local development mode, returns a local upload endpoint
 */
export async function generatePresignedUploadUrl(
  userId: string,
  originalFilename: string
): Promise<{ url: string; storageKey: string; expiresIn: number }> {
  const storageKey = generateStorageKey(userId, originalFilename);

  if (USE_LOCAL_STORAGE) {
    // In local mode, return a local upload endpoint
    logger.info(`Generated local upload URL for ${storageKey}`);
    return {
      url: `http://localhost:${process.env.PORT || 4000}/api/papers/upload/local/${encodeURIComponent(storageKey)}`,
      storageKey,
      expiresIn: PRESIGNED_URL_EXPIRES,
    };
  }

  const contentType = mime.lookup(originalFilename) || 'application/pdf';

  const command = new PutObjectCommand({
    Bucket: BUCKET_NAME,
    Key: storageKey,
    ContentType: contentType,
  });

  try {
    const url = await getSignedUrl(s3Client, command, {
      expiresIn: PRESIGNED_URL_EXPIRES,
    });

    logger.info(`Generated presigned URL for ${storageKey}`);

    return {
      url,
      storageKey,
      expiresIn: PRESIGNED_URL_EXPIRES,
    };
  } catch (error) {
    logger.error('Failed to generate presigned URL:', error);
    throw new Error('Failed to generate upload URL');
  }
}

/**
 * Upload file to local storage (for development)
 */
export async function uploadToLocalStorage(
  storageKey: string,
  fileBuffer: Buffer
): Promise<void> {
  const filePath = getLocalFilePath(storageKey);
  await fsPromises.mkdir(path.dirname(filePath), { recursive: true });
  await fsPromises.writeFile(filePath, fileBuffer);
  logger.info(`Saved file to local storage: ${filePath}`);
}

/**
 * Download object from storage to local file path
 * Used by Python worker to process the PDF
 */
export async function downloadForProcessing(
  storageKey: string,
  localPath: string
): Promise<void> {
  // If using local storage, copy from local storage path
  if (USE_LOCAL_STORAGE) {
    const sourcePath = getLocalFilePath(storageKey);
    try {
      await fsPromises.mkdir(path.dirname(localPath), { recursive: true });
      await fsPromises.copyFile(sourcePath, localPath);
      logger.info(`Copied file from local storage: ${sourcePath} -> ${localPath}`);
      return;
    } catch (error) {
      logger.error(`Failed to copy file from local storage: ${sourcePath}`, error);
      throw new Error(`Failed to download file: ${storageKey}`);
    }
  }

  const command = new GetObjectCommand({
    Bucket: BUCKET_NAME,
    Key: storageKey,
  });

  try {
    const response = await s3Client.send(command);

    if (!response.Body) {
      throw new Error('Empty response body from object storage');
    }

    // Ensure directory exists
    const dir = path.dirname(localPath);
    await fsPromises.mkdir(dir, { recursive: true });

    // Stream to file
    const fileStream = createWriteStream(localPath);
    const stream = response.Body as Readable;

    return new Promise((resolve, reject) => {
      stream.pipe(fileStream);
      fileStream.on('finish', resolve);
      fileStream.on('error', reject);
      stream.on('error', reject);
    });
  } catch (error) {
    logger.error(`Failed to download ${storageKey}:`, error);
    throw new Error(`Failed to download file: ${storageKey}`);
  }
}

/**
 * Generate a presigned URL for downloading from object storage
 */
export async function generatePresignedDownloadUrl(
  storageKey: string,
  expiresIn: number = PRESIGNED_URL_EXPIRES
): Promise<string> {
  if (USE_LOCAL_STORAGE) {
    // In local mode, return a direct file URL
    // Note: papers router is mounted at /api/papers
    return `http://localhost:${process.env.PORT || 4000}/api/papers/download/local/${encodeURIComponent(storageKey)}`;
  }

  const command = new GetObjectCommand({
    Bucket: BUCKET_NAME,
    Key: storageKey,
  });

  try {
    const url = await getSignedUrl(s3Client, command, {
      expiresIn,
    });

    logger.info(`Generated presigned download URL for ${storageKey}`);
    return url;
  } catch (error) {
    logger.error(`Failed to generate download URL for ${storageKey}:`, error);
    throw new Error(`Failed to generate download URL: ${storageKey}`);
  }
}

/**
 * Delete object from storage
 */
export async function deleteObject(storageKey: string): Promise<void> {
  if (USE_LOCAL_STORAGE) {
    const filePath = getLocalFilePath(storageKey);
    try {
      await fsPromises.unlink(filePath);
      logger.info(`Deleted file from local storage: ${filePath}`);
      return;
    } catch (error) {
      logger.error(`Failed to delete file from local storage: ${filePath}`, error);
      return; // Don't throw if file doesn't exist
    }
  }

  const command = new DeleteObjectCommand({
    Bucket: BUCKET_NAME,
    Key: storageKey,
  });

  try {
    await s3Client.send(command);
    logger.info(`Deleted object ${storageKey} from storage`);
  } catch (error) {
    logger.error(`Failed to delete ${storageKey}:`, error);
    throw new Error(`Failed to delete file: ${storageKey}`);
  }
}

/**
 * Check if object exists in storage
 */
export async function objectExists(storageKey: string): Promise<boolean> {
  if (USE_LOCAL_STORAGE) {
    const filePath = getLocalFilePath(storageKey);
    try {
      await fsPromises.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  const command = new GetObjectCommand({
    Bucket: BUCKET_NAME,
    Key: storageKey,
  });

  try {
    await s3Client.send(command);
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * Upload file buffer directly to storage and return URL
 * Used for avatar uploads and small files
 */
export async function uploadFile(
  userId: string,
  fileBuffer: Buffer,
  filename: string,
  contentType: string
): Promise<string> {
  const storageKey = filename;

  if (USE_LOCAL_STORAGE) {
    // Save to local storage
    const filePath = getLocalFilePath(storageKey);
    await fsPromises.mkdir(path.dirname(filePath), { recursive: true });
    await fsPromises.writeFile(filePath, fileBuffer);
    logger.info(`Uploaded file to local storage: ${filePath}`);
    // Return local URL
    return `http://localhost:${process.env.PORT || 4000}/api/download/local/${encodeURIComponent(storageKey)}`;
  }

  // Upload to S3/MinIO
  const command = new PutObjectCommand({
    Bucket: BUCKET_NAME,
    Key: storageKey,
    Body: fileBuffer,
    ContentType: contentType,
  });

  try {
    await s3Client.send(command);
    // Return public URL (MinIO/S3 format)
    const endpoint = process.env.OSS_ENDPOINT || '';
    const url = `${endpoint}/${BUCKET_NAME}/${storageKey}`;
    logger.info(`Uploaded file to object storage: ${url}`);
    return url;
  } catch (error) {
    logger.error('Failed to upload file:', error);
    throw new Error('Failed to upload file');
  }
}

/**
 * Get local file buffer for serving files
 * Only works in local storage mode
 */
export async function getLocalFileBuffer(storageKey: string): Promise<Buffer | null> {
  if (!USE_LOCAL_STORAGE) {
    return null;
  }

  try {
    const filePath = getLocalFilePath(storageKey);
    const buffer = await fsPromises.readFile(filePath);
    return buffer;
  } catch (error) {
    logger.error('Failed to read local file:', error);
    return null;
  }
}

export {
  s3Client,
  BUCKET_NAME,
  USE_LOCAL_STORAGE,
  LOCAL_STORAGE_PATH,
};
