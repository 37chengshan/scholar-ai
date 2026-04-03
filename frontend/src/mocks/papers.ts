// TODO: Replace with API call in future phase
// Mock data for Library page

export interface Paper {
  id: number;
  title: string;
  titleZh?: string;
  authors: string;
  year: number;
  venue: string;
  read: boolean;
  abstract: string;
  abstractZh?: string;
}

export const MOCK_PAPERS_EN: Paper[] = [
  {
    id: 1,
    title: "Attention Is All You Need",
    authors: "Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin",
    year: 2017,
    venue: "NeurIPS",
    read: true,
    abstract: "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer..."
  },
  {
    id: 2,
    title: "Language Models are Few-Shot Learners",
    authors: "Tom B. Brown, Benjamin Mann, Nick Ryder, Melanie Subbiah",
    year: 2020,
    venue: "NeurIPS",
    read: false,
    abstract: "Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by pre-training on a large corpus of text followed by fine-tuning on a specific task. While typically task-agnostic in architecture, this method still requires task-specific fine-tuning datasets of thousands or tens of thousands of examples..."
  },
  {
    id: 3,
    title: "RoBERTa: A Robustly Optimized BERT Pretraining Approach",
    authors: "Yinhan Liu, Myle Ott, Naman Goyal, Jingfei Du",
    year: 2019,
    venue: "arXiv",
    read: true,
    abstract: "Language model pretraining has led to significant performance gains but careful comparison between different approaches is challenging. Training is computationally expensive, often done on private datasets of different sizes, and, as we will show, hyperparameter choices have significant impact on the final results..."
  },
  {
    id: 4,
    title: "Scaling Laws for Neural Language Models",
    authors: "Jared Kaplan, Sam McCandlish, Tom Henighan, Tom B. Brown",
    year: 2020,
    venue: "arXiv",
    read: false,
    abstract: "We study empirical scaling laws for language model performance on the cross-entropy loss. The loss scales as a power-law with model size, dataset size, and the amount of compute used for training, with some trends spanning more than seven orders of magnitude..."
  },
  {
    id: 5,
    title: "BERT: Pre-training of Deep Bidirectional Transformers",
    authors: "Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova",
    year: 2019,
    venue: "NAACL",
    read: true,
    abstract: "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context..."
  },
  {
    id: 6,
    title: "InstructGPT: Training language models to follow instructions",
    authors: "Long Ouyang, Jeffrey Wu, Xu Jiang, Diogo Almeida",
    year: 2022,
    venue: "NeurIPS",
    read: true,
    abstract: "Making language models bigger does not inherently make them better at following a user's intent. For example, large language models can generate outputs that are untruthful, toxic, or simply not helpful to the user. In other words, these models are not aligned with their users. In this paper, we show an avenue for aligning language models..."
  }
];

export const MOCK_PAPERS_ZH: Paper[] = [
  {
    id: 1,
    title: "注意力机制就是你需要的一切",
    authors: "Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin",
    year: 2017,
    venue: "NeurIPS",
    read: true,
    abstract: "主要的序列转换模型基于复杂的循环或卷积神经网络，包括编码器和解码器。表现最好的模型还通过注意力机制连接编码器和解码器。我们提出了一种新的简单网络架构：Transformer..."
  },
  {
    id: 2,
    title: "语言模型是小样本学习者",
    authors: "Tom B. Brown, Benjamin Mann, Nick Ryder, Melanie Subbiah",
    year: 2020,
    venue: "NeurIPS",
    read: false,
    abstract: "最近的工作表明，通过在大量文本语料库上进行预训练，然后在特定任务上进行微调，在许多 NLP 任务和基准测试上取得了实质性进展。虽然架构通常与任务无关，但这仍然需要成千上万个示例的特定任务微调数据集..."
  },
  {
    id: 3,
    title: "RoBERTa：一种稳健优化的 BERT 预训练方法",
    authors: "Yinhan Liu, Myle Ott, Naman Goyal, Jingfei Du",
    year: 2019,
    venue: "arXiv",
    read: true,
    abstract: "语言模型预训练带来了显著的性能提升，但仔细比较不同方法具有挑战性。训练计算成本高昂，通常在不同大小的私有数据集上进行，正如我们将展示的，超参数的选择对最终结果有重大影响..."
  },
  {
    id: 4,
    title: "神经语言模型的缩放定律",
    authors: "Jared Kaplan, Sam McCandlish, Tom Henighan, Tom B. Brown",
    year: 2020,
    venue: "arXiv",
    read: false,
    abstract: "我们研究了语言模型性能在交叉熵损失上的经验缩放定律。损失随着模型大小、数据集大小和用于训练的计算量呈现幂律缩放，某些趋势跨越了七个以上的数量级..."
  },
  {
    id: 5,
    title: "BERT：深度双向 Transformer 预训练",
    authors: "Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova",
    year: 2019,
    venue: "NAACL",
    read: true,
    abstract: "我们引入了一种名为 BERT 的新语言表示模型，代表基于 Transformer 的双向编码器表示。与最近的语言表示模型不同，BERT 旨在通过联合调节左右上下文，从未标记文本中预训练深度双向表示..."
  },
  {
    id: 6,
    title: "InstructGPT：训练语言模型遵循指令",
    authors: "Long Ouyang, Jeffrey Wu, Xu Jiang, Diogo Almeida",
    year: 2022,
    venue: "NeurIPS",
    read: true,
    abstract: "将语言模型做大并不能本质上使它们更好地遵循用户的意图。例如，大型语言模型可能会生成不真实的、有毒的或对用户根本没有帮助的输出。换句话说，这些模型与用户没有对齐。在本文中，我们展示了对齐语言模型的途径..."
  }
];

// Helper function to get papers based on language
export function getMockPapers(isZh: boolean): Paper[] {
  return isZh ? MOCK_PAPERS_ZH : MOCK_PAPERS_EN;
}