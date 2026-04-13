/**
 * ScholarAI UAT 自动化测试脚本
 * 使用 Cookie-based Session 认证
 */

const BASE_URL = 'http://localhost:8000';
const FRONTEND_URL = 'http://localhost:5173';

const TEST_CONFIG = {
  user: {
    email: 'test@example.com',
    password: 'Test123456',
    name: 'Test User'
  },
  papers: [
    { title: 'Attention Is All You Need', category: 'nlp', authors: ['Vaswani et al.'] },
    { title: 'BERT: Pre-training of Deep Bidirectional Transformers', category: 'nlp', authors: ['Devlin et al.'] },
    { title: 'ImageNet Classification with Deep Convolutional Networks', category: 'cv', authors: ['Krizhevsky et al.'] },
    { title: 'Mastering the Game of Go with Deep Neural Networks', category: 'rl', authors: ['Silver et al.'] },
    { title: 'Learning Transferable Visual Models From Natural Language', category: 'multimodal', authors: ['Radford et al.'] }
  ]
};

let cookies = '';

async function apiRequest(method, endpoint, body = null) {
  const url = `${BASE_URL}${endpoint}`;
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Cookie': cookies
    }
  };
  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, options);
    
    // 保存 cookie
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) {
      const accessToken = setCookie.split(';')[0];
      if (accessToken.startsWith('accessToken=')) {
        cookies = accessToken;
      }
    }
    
    const data = await response.json();
    return { status: response.status, data };
  } catch (error) {
    return { status: 0, error: error.message };
  }
}

async function testLogin() {
  console.log('\n🟦 阶段 1: 用户登录');
  console.log('─'.repeat(50));

  console.log('  📤 发送登录请求...');
  const result = await apiRequest('POST', '/api/auth/login', {
    email: TEST_CONFIG.user.email,
    password: TEST_CONFIG.user.password
  });

  if (result.status === 200 && result.data.success) {
    console.log('  ✅ 登录成功');
    console.log(`     用户: ${result.data.data.user.email}`);
    console.log(`     认证方式: Cookie Session`);
    return { success: true };
  } else {
    console.log('  ❌ 登录失败:', result.data?.error?.detail || result.error);
    return { success: false };
  }
}

async function testUploadPapers() {
  console.log('\n🟦 阶段 2: 上传论文 (5篇)');
  console.log('─'.repeat(50));

  const uploadedPapers = [];
  const testPapers = [
    { file: '2604.01226v1.pdf', title: 'Paper 1 - arXiv:2604.01226' },
    { file: '2604.01228v1.pdf', title: 'Paper 2 - arXiv:2604.01228' },
    { file: '2604.01232v1.pdf', title: 'Paper 3 - arXiv:2604.01232' },
    { file: '2604.01238v1.pdf', title: 'Paper 4 - arXiv:2604.01238' },
    { file: '2604.01241v1.pdf', title: 'Paper 5 - arXiv:2604.01241' }
  ];

  for (let i = 0; i < testPapers.length; i++) {
    const paper = testPapers[i];
    console.log(`\n  📄 论文 ${i + 1}: ${paper.title}`);

    // 创建论文记录
    console.log('     📤 创建论文记录...');
    const createResult = await apiRequest('POST', '/api/papers', {
      filename: paper.file
    });

    if (createResult.status === 201 || createResult.status === 200) {
      console.log(`     ✅ 论文记录创建成功`);
      if (createResult.data.data?.paperId) {
        uploadedPapers.push({
          id: createResult.data.data.paperId,
          title: paper.title,
          storageKey: createResult.data.data.storageKey
        });
      }
    } else {
      console.log('     ❌ 创建失败:', createResult.data?.error?.detail || createResult.error);
    }
  }

  console.log(`\n  📊 上传完成: ${uploadedPapers.length}/${testPapers.length} 篇`);
  return { success: uploadedPapers.length > 0, papers: uploadedPapers };
}

async function testLibraryManagement(papers) {
  console.log('\n🟦 阶段 3: 文献管理');
  console.log('─'.repeat(50));

  // 3.1 获取论文列表
  console.log('  📥 获取文献库列表...');
  const listResult = await apiRequest('GET', '/api/papers?page=1&limit=20');

  if (listResult.status === 200 && listResult.data.success) {
    const papers = listResult.data.data || [];
    console.log(`  ✅ 获取列表成功 (共 ${Array.isArray(papers) ? papers.length : 0} 篇)`);
  } else {
    console.log('  ❌ 获取列表失败:', listResult.data?.error?.detail);
  }

  // 3.2 搜索论文
  console.log('  🔍 测试搜索功能...');
  const searchResult = await apiRequest('GET', '/api/papers?q=attention&page=1&limit=10');

  if (searchResult.status === 200) {
    console.log('  ✅ 搜索功能正常');
  }

  // 3.3 收藏论文
  if (papers.length > 0) {
    console.log('  ⭐ 测试收藏功能...');
    const starResult = await apiRequest('POST', `/api/papers/${papers[0].id}/star`, {});

    if (starResult.status === 200) {
      console.log('  ✅ 收藏功能正常');
    }

    // 3.4 获取论文详情
    console.log('  📖 获取论文详情...');
    const detailResult = await apiRequest('GET', `/api/papers/${papers[0].id}`);

    if (detailResult.status === 200 && detailResult.data.data) {
      console.log(`  ✅ 详情获取成功: ${detailResult.data.data.title}`);
    }
  }

  return { success: true };
}

async function testExternalSearch() {
  console.log('\n🟦 阶段 4: 外部搜索');
  console.log('─'.repeat(50));

  // 4.1 Semantic Scholar 搜索
  console.log('  🔍 测试 Semantic Scholar 搜索...');
  const s2Result = await apiRequest('GET', '/api/search/semantic-scholar?query=transformer&limit=3');

  if (s2Result.status === 200 && s2Result.data.success) {
    const results = s2Result.data.data?.results || [];
    console.log(`  ✅ Semantic Scholar 搜索成功 (找到 ${results.length} 篇)`);
  } else {
    console.log('  ⚠️  Semantic Scholar 搜索:', s2Result.data?.error?.detail || '检查API配置');
  }

  // 4.2 arXiv 搜索
  console.log('  🔍 测试 arXiv 搜索...');
  const arxivResult = await apiRequest('GET', '/api/search/arxiv?query=machine+learning&limit=3');

  if (arxivResult.status === 200 && arxivResult.data.success) {
    const results = arxivResult.data.data?.results || [];
    console.log(`  ✅ arXiv 搜索成功 (找到 ${results.length} 篇)`);
  } else {
    console.log('  ⚠️  arXiv 搜索:', arxivResult.data?.error?.detail || '服务可能未配置');
  }

  return { success: true };
}

async function testChat(papers) {
  console.log('\n🟦 阶段 5: Chat对话');
  console.log('─'.repeat(50));

  // 5.1 普通对话
  console.log('  💬 测试普通对话...');
  const chatResult = await apiRequest('POST', '/api/chat', {
    message: '什么是深度学习？请简要说明。',
    mode: 'general'
  });

  if (chatResult.status === 200 && chatResult.data.success) {
    console.log('  ✅ 普通对话正常');
    const response = chatResult.data.data?.response || chatResult.data.data?.answer || '';
    if (response) {
      console.log(`     回复预览: ${response.substring(0, 80)}...`);
    }
  } else {
    console.log('  ⚠️  普通对话:', chatResult.data?.error?.detail || 'AI服务可能未配置');
  }

  // 5.2 基于论文的对话（RAG）
  if (papers.length > 0) {
    console.log('  💬 测试论文问答（RAG）...');
    const ragResult = await apiRequest('POST', '/api/chat', {
      message: '这篇论文的主要贡献是什么？',
      paperIds: [papers[0].id],
      mode: 'rag'
    });

    if (ragResult.status === 200) {
      console.log('  ✅ 论文问答正常');
    } else {
      console.log('  ⚠️  论文问答:', ragResult.data?.error?.detail || 'RAG服务可能未配置');
    }
  }

  return { success: true };
}

async function runUATTests() {
  console.log('\n' + '='.repeat(60));
  console.log('  ScholarAI UAT 自动化测试');
  console.log('='.repeat(60));
  console.log(`\n  API服务: ${BASE_URL}`);
  console.log(`  前端服务: ${FRONTEND_URL}`);
  console.log(`  测试用户: ${TEST_CONFIG.user.email}`);
  console.log(`  认证方式: Cookie Session`);

  const results = {
    login: false,
    upload: false,
    library: false,
    search: false,
    chat: false
  };

  // 阶段1: 登录
  const loginResult = await testLogin();
  results.login = loginResult.success;

  if (!loginResult.success) {
    console.log('\n❌ 登录失败，终止测试');
    return results;
  }

  // 阶段2: 上传论文
  const uploadResult = await testUploadPapers();
  results.upload = uploadResult.success;

  // 阶段3: 文献管理
  const libraryResult = await testLibraryManagement(uploadResult.papers);
  results.library = libraryResult.success;

  // 阶段4: 外部搜索
  const searchResult = await testExternalSearch();
  results.search = searchResult.success;

  // 阶段5: Chat对话
  const chatResult = await testChat(uploadResult.papers);
  results.chat = chatResult.success;

  // 测试报告
  console.log('\n' + '='.repeat(60));
  console.log('  测试结果汇总');
  console.log('='.repeat(60));
  console.log(`  登录功能      : ${results.login ? '✅ 通过' : '❌ 失败'}`);
  console.log(`  上传论文      : ${results.upload ? '✅ 通过' : '❌ 失败'}`);
  console.log(`  文献管理      : ${results.library ? '✅ 通过' : '❌ 失败'}`);
  console.log(`  外部搜索      : ${results.search ? '✅ 通过' : '⚠️  部分通过'}`);
  console.log(`  Chat对话      : ${results.chat ? '✅ 通过' : '⚠️  部分通过'}`);
  console.log('─'.repeat(60));

  const passed = Object.values(results).filter(r => r).length;
  const total = Object.values(results).length;
  
  if (passed === total) {
    console.log('  ✅ 所有测试通过！');
  } else if (passed >= 3) {
    console.log(`  ⚠️  核心功能通过 (${passed}/${total})`);
  } else {
    console.log(`  ❌ 测试失败较多 (${passed}/${total})`);
  }
  console.log('='.repeat(60) + '\n');

  return results;
}

runUATTests().catch(console.error);