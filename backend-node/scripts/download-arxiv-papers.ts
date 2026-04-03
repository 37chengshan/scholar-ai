import https from 'https';
import fs from 'fs';
import path from 'path';

const ARXIV_PAPER_IDS = [
  '2301.07041',  // LLaMA: Open and Efficient Foundation Language Models
  '2303.08774',  // GPT-4 Technical Report
  '2005.14165',  // Language Models are Few-Shot Learners (GPT-3)
  '1810.04805',  // BERT: Pre-training of Deep Bidirectional Transformers
  '1706.03762',  // Attention Is All You Need (Transformer)
  '2203.02155',  // Training language models to follow instructions with human feedback (InstructGPT)
  '2103.00020',  // CLIP: Learning Transferable Visual Models
  '1911.02147',  // Extracting Training Data from Large Language Models
  '2004.05150',  // ELECTRA: Pre-training Text Encoders
  '2110.08295',  // Chain-of-Thought Prompting Elicits Reasoning
];

const OUTPUT_DIR = path.join(__dirname, 'arxiv-papers');

function downloadArxivPaper(arxivId: string): Promise<string> {
  const url = `https://arxiv.org/pdf/${arxivId}.pdf`;
  const outputPath = path.join(OUTPUT_DIR, `${arxivId}.pdf`);

  return new Promise((resolve, reject) => {
    console.log(`Downloading ${arxivId}...`);

    if (!fs.existsSync(OUTPUT_DIR)) {
      fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    }

    const file = fs.createWriteStream(outputPath);

    https.get(url, (response) => {
      if (response.statusCode === 200) {
        response.pipe(file);
        file.on('finish', () => {
          file.close();
          console.log(`✓ Downloaded ${arxivId} to ${outputPath}`);
          resolve(outputPath);
        });
      } else if (response.statusCode === 301 || response.statusCode === 302) {
        const redirectUrl = response.headers.location;
        if (redirectUrl) {
          const fullRedirectUrl = redirectUrl.startsWith('http') 
            ? redirectUrl 
            : `https://arxiv.org${redirectUrl}`;
          https.get(fullRedirectUrl, (redirectResponse) => {
            redirectResponse.pipe(file);
            file.on('finish', () => {
              file.close();
              console.log(`✓ Downloaded ${arxivId} to ${outputPath}`);
              resolve(outputPath);
            });
          }).on('error', reject);
        } else {
          reject(new Error(`Redirect without location for ${arxivId}`));
        }
      } else {
        reject(new Error(`Failed to download ${arxivId}: Status ${response.statusCode}`));
      }
    }).on('error', (err) => {
      fs.unlink(outputPath, () => {});
      reject(err);
    });
  });
}

async function downloadAllPapers() {
  console.log('Starting download of 10 arXiv papers...\n');

  const results: { arxivId: string; path: string; error?: string }[] = [];

  for (const arxivId of ARXIV_PAPER_IDS) {
    try {
      const outputPath = await downloadArxivPaper(arxivId);
      results.push({ arxivId, path: outputPath });
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      console.error(`✗ Failed to download ${arxivId}: ${errorMsg}`);
      results.push({ arxivId, path: '', error: errorMsg });
    }
  }

  console.log('\n========================================');
  console.log('Download Summary');
  console.log('========================================\n');

  const successful = results.filter(r => !r.error);
  const failed = results.filter(r => r.error);

  console.log(`Total: ${results.length} papers`);
  console.log(`Successful: ${successful.length}`);
  console.log(`Failed: ${failed.length}\n`);

  if (successful.length > 0) {
    console.log('Successfully downloaded:');
    successful.forEach(r => console.log(`  ✓ ${r.arxivId}: ${r.path}`));
  }

  if (failed.length > 0) {
    console.log('\nFailed to download:');
    failed.forEach(r => console.log(`  ✗ ${r.arxivId}: ${r.error}`));
  }

  return results;
}

downloadAllPapers().catch(console.error);