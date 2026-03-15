import request from 'supertest';
import app from '../../src/index';
import { generateTestUserData, cleanupTestData } from '../helpers/db';

describe('Authentication E2E Tests', () => {
  afterAll(async () => {
    await cleanupTestData();
  });

  describe('POST /api/auth/register', () => {
    it('should register a new user successfully', async () => {
      const testData = generateTestUserData();

      const response = await request(app)
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toMatchObject({
        email: testData.email,
        name: testData.name,
        emailVerified: true,
      });
      expect(response.body.data.id).toBeDefined();
      expect(response.body.data.roles).toContain('user');
      expect(response.body.meta).toBeDefined();
    });

    it('should return 409 for duplicate email', async () => {
      const testData = generateTestUserData();

      // Register first user
      await request(app)
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      // Try to register again with same email
      const response = await request(app)
        .post('/api/auth/register')
        .send(testData)
        .expect(409);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/conflict');
      expect(response.body.error.detail).toContain('already registered');
    });

    it('should return 400 for invalid email format', async () => {
      const response = await request(app)
        .post('/api/auth/register')
        .send({
          email: 'invalid-email',
          password: 'Test123!',
          name: 'Test User',
        })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/validation-error');
    });

    it('should return 400 for weak password', async () => {
      const testData = generateTestUserData();

      const response = await request(app)
        .post('/api/auth/register')
        .send({
          email: testData.email,
          password: '123', // Too weak
          name: testData.name,
        })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/validation-error');
    });

    it('should return 400 for short name', async () => {
      const testData = generateTestUserData();

      const response = await request(app)
        .post('/api/auth/register')
        .send({
          email: testData.email,
          password: 'Test123!',
          name: 'A', // Too short
        })
        .expect(400);

      expect(response.body.success).toBe(false);
    });
  });

  describe('POST /api/auth/login', () => {
    it('should login with valid credentials and set cookies', async () => {
      const testData = generateTestUserData();

      // Register first
      await request(app)
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      // Login
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: testData.email,
          password: testData.password,
        })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.user).toMatchObject({
        email: testData.email,
        name: testData.name,
      });
      expect(response.body.data.user.roles).toContain('user');

      // Check cookies are set
      const cookies = response.headers['set-cookie'];
      expect(cookies).toBeDefined();
      expect(cookies.some((c: string) => c.includes('accessToken'))).toBe(true);
      expect(cookies.some((c: string) => c.includes('refreshToken'))).toBe(true);
      // Check httpOnly flag
      expect(cookies.some((c: string) => c.includes('HttpOnly'))).toBe(true);
    });

    it('should return 401 for invalid password', async () => {
      const testData = generateTestUserData();

      // Register first
      await request(app)
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      // Login with wrong password
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: testData.email,
          password: 'WrongPassword123!',
        })
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/invalid-credentials');
    });

    it('should return 401 for non-existent user', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'nonexistent@example.com',
          password: 'Test123!',
        })
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.type).toBe('/errors/invalid-credentials');
    });
  });

  describe('GET /api/auth/me', () => {
    it('should return user info with valid token', async () => {
      const testData = generateTestUserData();
      const agent = request.agent(app);

      // Register and login
      await agent
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      const loginRes = await agent
        .post('/api/auth/login')
        .send({
          email: testData.email,
          password: testData.password,
        })
        .expect(200);

      // Get user info
      const response = await agent
        .get('/api/auth/me')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toMatchObject({
        email: testData.email,
        name: testData.name,
      });
    });

    it('should return 401 without authentication', async () => {
      const response = await request(app)
        .get('/api/auth/me')
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.status).toBe(401);
    });
  });

  describe('POST /api/auth/logout', () => {
    it('should logout and clear cookies', async () => {
      const testData = generateTestUserData();
      const agent = request.agent(app);

      // Register and login
      await agent
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      await agent
        .post('/api/auth/login')
        .send({
          email: testData.email,
          password: testData.password,
        })
        .expect(200);

      // Logout
      const response = await agent
        .post('/api/auth/logout')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.message).toContain('Logged out');

      // Check cookies are cleared
      const cookies = response.headers['set-cookie'];
      if (cookies) {
        expect(cookies.some((c: string) => c.includes('accessToken='))).toBe(true);
      }
    });

    it('should handle logout without being logged in', async () => {
      const response = await request(app)
        .post('/api/auth/logout')
        .expect(200);

      expect(response.body.success).toBe(true);
    });
  });

  describe('POST /api/auth/refresh', () => {
    it('should refresh access token with valid refresh token', async () => {
      const testData = generateTestUserData();
      const agent = request.agent(app);

      // Register and login
      await agent
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      await agent
        .post('/api/auth/login')
        .send({
          email: testData.email,
          password: testData.password,
        })
        .expect(200);

      // Refresh token
      const response = await agent
        .post('/api/auth/refresh')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.message).toContain('refreshed');

      // Check new cookies are set
      const cookies = response.headers['set-cookie'];
      expect(cookies).toBeDefined();
      expect(cookies.some((c: string) => c.includes('accessToken'))).toBe(true);
    });

    it('should return 401 without refresh token', async () => {
      const response = await request(app)
        .post('/api/auth/refresh')
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error.status).toBe(401);
    });
  });
});
