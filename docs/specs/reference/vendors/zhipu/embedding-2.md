> ## Documentation Index
> Fetch the complete documentation index at: https://docs.bigmodel.cn/llms.txt
> Use this file to discover all available pages before exploring further.

# Embedding-2

## <div className="flex items-center"> <svg style={{maskImage: "url(/resource/icon/rectangle-list.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} /> 概览 </div>

Embedding-2 是智谱AI 推出的第二代文本向量化模型，能够将文本转换为高维向量表示，用于语义相似性计算和搜索。该模型在语义理解、文本检索和相似度计算方面表现优异，适用于构建智能搜索、推荐系统和知识库等应用。

<CardGroup cols={3}>
  <Card title="价格" icon={<svg style={{maskImage: "url(/resource/icon/coins.svg)", WebkitMaskImage: "url(/resource/icon/coins.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} />}>
    0.5 元 / 百万 Tokens
  </Card>

  <Card title="输入模态" icon={<svg style={{maskImage: "url(/resource/icon/arrow-down-right.svg)", WebkitMaskImage: "url(/resource/icon/arrow-down-right.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} />}>
    文本
  </Card>

  <Card title="输出模态" icon={<svg style={{maskImage: "url(/resource/icon/arrow-down-left.svg)", WebkitMaskImage: "url(/resource/icon/arrow-down-left.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} />}>
    向量
  </Card>

  <Card title="上下文窗口" icon={<svg style={{maskImage: "url(/resource/icon/arrow-down-arrow-up.svg)", WebkitMaskImage: "url(/resource/icon/arrow-down-arrow-up.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} />}>
    8K
  </Card>

  <Card title="向量维度" icon={<svg style={{maskImage: "url(/resource/icon/maximize.svg)", WebkitMaskImage: "url(/resource/icon/maximize.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} />}>
    1024
  </Card>
</CardGroup>

## <div className="flex items-center"> <svg style={{maskImage: "url(/resource/icon/stars.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} /> 推荐场景 </div>

<AccordionGroup>
  <Accordion title="语义搜索" defaultOpen>
    将用户查询和文档库转换为向量，通过计算向量相似度实现精准的语义搜索，能够理解查询意图而非仅仅匹配关键词。
  </Accordion>

  <Accordion title="文本聚类" defaultOpen>
    将相似主题的文本聚集在一起，用于内容分类、主题发现和文档整理，帮助用户快速理解大量文本的主要内容。
  </Accordion>

  <Accordion title="推荐系统" defaultOpen>
    基于用户历史行为和内容向量化，计算用户偏好与内容的相似度，实现个性化内容推荐。
  </Accordion>

  <Accordion title="异常检测" defaultOpen>
    通过计算文本向量与正常样本的距离，识别异常或可疑内容，用于内容审核和风险控制。
  </Accordion>

  <Accordion title="知识库问答" defaultOpen>
    将知识库文档向量化，通过语义匹配找到与用户问题最相关的文档片段，提供准确的答案。
  </Accordion>
</AccordionGroup>

## <div className="flex items-center"> <svg style={{maskImage: "url(/resource/icon/gauge-high.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} /> 使用资源 </div>

[体验中心](https://bigmodel.cn/trialcenter)：快速测试模型在业务场景上的效果<br />
[接口文档](/api-reference/%E6%A8%A1%E5%9E%8B-api/%E6%96%87%E6%9C%AC%E5%B5%8C%E5%85%A5)：API 调用方式

## <div className="flex items-center"> <svg style={{maskImage: "url(/resource/icon/arrow-up.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} /> 详细介绍 </div>

<Steps>
  <Step title="模型特性" titleSize="h3">
    Embedding-2 采用先进的神经网络架构，能够深度理解文本的语义信息。模型支持中英文等多种语言，在保持高质量向量表示的同时，具有良好的计算效率。

    **核心特性：**

    * **多语言支持**：支持中文、英文等多种语言的文本向量化
    * **语义理解**：能够捕捉文本的深层语义信息，而非仅仅是词汇匹配
    * **高效计算**：优化的模型架构确保快速的向量生成速度
    * **稳定输出**：相同输入始终产生一致的向量表示
  </Step>

  <Step title="技术规格" stepNumber={2} titleSize="h3">
    Embedding-2 提供 1024 维的向量输出，支持最大 8K tokens 的文本输入。模型经过大规模多语言语料训练，在各种文本类型上都有良好的表现。

    **技术参数：**

    * 向量维度：1024 维
    * 输入字符串数组中，单条请求最多支持 512 个 Tokens，数组总长度不得超过 8K
  </Step>
</Steps>

## <div className="flex items-center"> <svg style={{maskImage: "url(/resource/icon/code.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} /> 调用示例 </div>

以下是一个完整的调用示例，帮助您快速上手 Embedding-2 模型。

<Tabs>
  <Tab title="cURL">
    ```bash  theme={null}
    curl -X POST \
    https://open.bigmodel.cn/api/paas/v4/embeddings \
    -H "Authorization: Bearer your-api-key" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "embedding-2",
        "input": "这是一段需要向量化的文本"
    }'
    ```
  </Tab>

  <Tab title="python">
    **安装 SDK**

    ```bash  theme={null}
    # 安装最新版本
    pip install zai-sdk
    # 或指定版本
    pip install zai-sdk==0.2.2
    ```

    **验证安装**

    ```python  theme={null}
    import zai
    print(zai.__version__)
    ```

    **调用示例**

    ```python  theme={null}
    from zai import ZhipuAiClient

    client = ZhipuAiClient(api_key="your-api-key")
    response = client.embeddings.create(
        model="embedding-2",  # 填写需要调用的模型编码
        input=[
            "美食非常美味，服务员也很友好。",
            "这部电影既刺激又令人兴奋。",
            "阅读书籍是扩展知识的好方法。"
        ],
    )
    print(response)
    ```
  </Tab>

  <Tab title="Java">
    **安装 SDK**

    **Maven**

    ```xml  theme={null}
    <dependency>
        <groupId>ai.z.openapi</groupId>
        <artifactId>zai-sdk</artifactId>
        <version>0.3.3</version>
    </dependency>
    ```

    **Gradle (Groovy)**

    ```groovy  theme={null}
    implementation 'ai.z.openapi:zai-sdk:0.3.3'
    ```

    **调用示例**

    ```java  theme={null}
    import ai.z.openapi.ZhipuAiClient;
    import ai.z.openapi.service.embedding.EmbeddingCreateParams;
    import ai.z.openapi.service.embedding.EmbeddingResponse;
    import java.util.Arrays;
    import java.util.List;

    public class EmbeddingExample {
        public static void main(String[] args) {
            // 初始化客户端
            ZhipuAiClient client = ZhipuAiClient.builder().ofZHIPU()
                .apiKey("your-api-key")
                .build();

            // 创建向量化请求
            EmbeddingCreateParams request = EmbeddingCreateParams.builder()
                .model("embedding-2")
                .input(Arrays.asList("Hello world", "How are you?", "How is the weather today?"))
                .build();

            // 发送请求
            EmbeddingResponse response = client.embeddings().createEmbeddings(request);
            System.out.println("向量: " + response.getData());
        }
    }
    ```
  </Tab>

  <Tab title="Python(旧)">
    ```python  theme={null}
    from zhipuai import ZhipuAI

    client = ZhipuAI(api_key="your-api-key")
    response = client.embeddings.create(
        model="embedding-2",  # 填写需要调用的模型编码
        input=[
            "美食非常美味，服务员也很友好。",
            "这部电影既刺激又令人兴奋。",
            "阅读书籍是扩展知识的好方法。"
        ],
    )
    print(response)
    ```
  </Tab>

  <Tab title="响应示例">
    ```json  theme={null}
    {
        "model": "embedding-2",
        "data": [
            {
                "embedding": [
                    -0.02675454691052437,
                    0.019060475751757622,
                    ......
                    -0.005519774276763201,
                    0.014949671924114227
        ],
                "index": 0,
                "object": "embedding"
            },
            ...
            {
                "embedding": [
                    -0.02675454691052437,
                    0.019060475751757622,
                    ......
                    -0.005519774276763201,
                    0.014949671924114227
                ],
                "index": 2,
                "object": "embedding"
            }
        ],
        "object": "list",
        "usage": {
            "completion_tokens": 0,
        "prompt_tokens": 100,
            "total_tokens": 100
        }
    }
    ```
  </Tab>
</Tabs>

## <div className="flex items-center"> <svg style={{maskImage: "url(/resource/icon/feather.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} /> 最佳实践 </div>

<AccordionGroup>
  <Accordion title="文本预处理">
    在向量化之前，建议对文本进行适当的预处理：

    * 去除多余的空格和特殊字符
    * 统一文本格式（如大小写）
    * 对于长文本，考虑分段处理以获得更好的语义表示
  </Accordion>

  <Accordion title="相似度计算">
    使用余弦相似度计算向量间的相似性：

    ```python  theme={null}
    import numpy as np

    def cosine_similarity(vec1, vec2):
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    ```
  </Accordion>

  <Accordion title="批量处理">
    为提高效率，建议批量处理多个文本：

    * 单次最多处理 8K 长度文本
    * 合理安排批次大小以平衡速度和资源使用
  </Accordion>
</AccordionGroup>

## <div className="flex items-center"> <svg style={{maskImage: "url(/resource/icon/square-user.svg)", maskRepeat: "no-repeat", maskPosition: "center center",}} className={"h-6 w-6 bg-primary dark:bg-primary-light !m-0 shrink-0"} /> 用户并发权益 </div>

API调用会受到速率限制，当前我们限制的维度是请求并发数量（在途请求任务数量）。不同等级的用户并发保障如下。

| V0 | V1  | V2  | V3  |
| :- | :-- | :-- | :-- |
| 50 | 100 | 300 | 500 |


Built with [Mintlify](https://mintlify.com).ßß