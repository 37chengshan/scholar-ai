import request from 'supertest';
import app from '../../src/index';
import { generateTestUserData } from './db';

/**
 * Create a supertest agent for making requests
 */
export function createTestAgent() {
  return request.agent(app);
}

/**
 * Register and login a test user, returning the agent with cookies set
 */
export async function createAuthenticatedUser(role: 'user' | 'admin' = 'user') {
  const agent = createTestAgent();
  const testData = generateTestUserData();

  // Register
  const registerRes = await agent
    .post('/api/auth/register')
    .send(testData)
    .expect(201);

  // Login (cookies will be set automatically)
  const loginRes = await agent
    .post('/api/auth/login')
    .send({
      email: testData.email,
      password: testData.password,
    })
    .expect(200);

  return {
    agent,
    user: loginRes.body.data.user,
    email: testData.email,
    password: testData.password,
  };
}

/**
 * Make an authenticated request with Bearer token
 */
export function authRequest(agent: request.SuperAgentTest, token: string) {
  return {
    get: (url: string) => agent.get(url).set('Authorization', `Bearer ${token}`),
    post: (url: string) => agent.post(url).set('Authorization', `Bearer ${token}`),
    put: (url: string) => agent.put(url).set('Authorization', `Bearer ${token}`),
    delete: (url: string) => agent.delete(url).set('Authorization', `Bearer ${token}`),
  };
}
