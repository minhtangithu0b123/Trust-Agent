# TÀI LIỆU HƯỚNG DẪN HỌC TẬP VÀ PHÁT TRIỂN KỸ NĂNG TOÀN DIỆN (COMPREHENSIVE LEARNING & SKILL DEVELOPMENT GUIDE)

**Dự án**: Trust-AGENT — Vietnamese Multi-Agent Legal RAG Platform & Web3 Commercialization  
**Tài liệu tham chiếu**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, `docs/GAP_ANALYSIS.md`  
**Phiên bản**: 1.0.0 (Official Curriculum Release)  
**Tác giả**: Worker 3 (Principal AI/Web3 Curriculum Specialist & Technical Educator)  
**Phạm vi áp dụng**: Đào tạo Kỹ sư AI/Fullstack, Kỹ sư Hệ thống Web3, và Kiến trúc sư Hệ thống Tác tử Pháp lý  

---

## MỤC LỤC

1. [TỔNG QUAN VÀ KHUNG NĂNG LỰC CỐT LÕI (OVERVIEW & COMPETENCY FRAMEWORK)](#1-tổng-quan-và-khung-năng-lực-cốt-lõi-overview--competency-framework)
   - [1.1. Bối cảnh kỹ thuật và Khoảng cách năng lực cần lấp đầy](#11-bối-cảnh-kỹ-thuật-và-khoảng-cách-năng-lực-cần-lấp-đầy)
   - [1.2. Ma trận năng lực chữ T (T-Shaped Competency Matrix)](#12-ma-trận-năng-lực-chữ-t-t-shaped-competency-matrix)
   - [1.3. Yêu cầu tiên quyết (Prerequisites)](#13-yêu-cầu-tiên-quyết-prerequisites)
2. [MODULE 1: HỆ THỐNG MULTI-AGENT & KỸ THUẬT ĐIỀU PHỐI (MULTI-AGENT ORCHESTRATION)](#2-module-1-hệ-thống-multi-agent--kỹ-thuật-điều-phối-multi-agent-orchestration)
   - [2.1. Kiến thức cốt lõi (Core Concepts)](#21-kiến-thức-cốt-lõi-core-concepts)
   - [2.2. Kỹ năng thực hành (Practical Skills)](#22-kỹ-năng-thực-hành-practical-skills)
   - [2.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)](#23-giáo-trình-nghiên-cứu--sách-kinh-điển-research-papers--books)
   - [2.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)](#24-tiêu-chuẩn-và-đặc-tả-kỹ-thuật-official-standards--specs)
   - [2.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)](#25-dự-án-mã-nguồn-mở-tham-khảo-open-source-reference-repositories)
3. [MODULE 2: ADVANCED LEGAL RAG CHO VĂN BẢN QUY PHẠM PHÁP LUẬT VIỆT NAM](#3-module-2-advanced-legal-rag-cho-văn-bản-quy-phạm-pháp-luật-việt-nam)
   - [3.1. Kiến thức cốt lõi (Core Concepts)](#31-kiến-thức-cốt-lõi-core-concepts)
   - [3.2. Kỹ năng thực hành (Practical Skills)](#32-kỹ-năng-thực-hành-practical-skills)
   - [3.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)](#33-giáo-trình-nghiên-cứu--sách-kinh-điển-research-papers--books)
   - [3.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)](#34-tiêu-chuẩn-và-đặc-tả-kỹ-thuật-official-standards--specs)
   - [3.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)](#35-dự-án-mã-nguồn-mở-tham-khảo-open-source-reference-repositories)
4. [MODULE 3: GIAO THỨC THANH TOÁN X402 & KINH TẾ TÁC TỬ (AGENTIC COMMERCE)](#4-module-3-giao-thức-thanh-toán-x402--kinh-tế-tác-tử-agentic-commerce)
   - [4.1. Kiến thức cốt lõi (Core Concepts)](#41-kiến-thức-cốt-lõi-core-concepts)
   - [4.2. Kỹ năng thực hành (Practical Skills)](#42-kỹ-năng-thực-hành-practical-skills)
   - [4.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)](#43-giáo-trình-nghiên-cứu--sách-kinh-điển-research-papers--books)
   - [4.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)](#44-tiêu-chuẩn-và-đặc-tả-kỹ-thuật-official-standards--specs)
   - [4.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)](#45-dự-án-mã-nguồn-mở-tham-khảo-open-source-reference-repositories)
5. [MODULE 4: CHUẨN ERC-8004 & PHÁT TRIỂN SMART CONTRACT TRÊN EVM](#5-module-4-chuẩn-erc-8004--phát-triển-smart-contract-trên-evm)
   - [5.1. Kiến thức cốt lõi (Core Concepts)](#51-kiến-thức-cốt-lõi-core-concepts)
   - [5.2. Kỹ năng thực hành (Practical Skills)](#52-kỹ-năng-thực-hành-practical-skills)
   - [5.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)](#53-giáo-trình-nghiên-cứu--sách-kinh-điển-research-papers--books)
   - [5.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)](#54-tiêu-chuẩn-và-đặc-tả-kỹ-thuật-official-standards--specs)
   - [5.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)](#55-dự-án-mã-nguồn-mở-tham-khảo-open-source-reference-repositories)
6. [MODULE 5: CƠ CHẾ MÃ HÓA BẰNG CHỨNG XUẤT XỨ (CRYPTOGRAPHIC PROVENANCE) & ON-CHAIN MERKLE BATCHING](#6-module-5-cơ-chế-mã-hóa-bằng-chứng-xuất-xứ-cryptographic-provenance--on-chain-merkle-batching)
   - [6.1. Kiến thức cốt lõi (Core Concepts)](#61-kiến-thức-cốt-lõi-core-concepts)
   - [6.2. Kỹ năng thực hành (Practical Skills)](#62-kỹ-năng-thực-hành-practical-skills)
   - [6.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)](#63-giáo-trình-nghiên-cứu--sách-kinh-điển-research-papers--books)
   - [6.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)](#64-tiêu-chuẩn-và-đặc-tả-kỹ-thuật-official-standards--specs)
   - [6.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)](#65-dự-án-mã-nguồn-mở-tham-khảo-open-source-reference-repositories)
7. [MODULE 6: CƠ CHẾ KINH TẾ TOKEN & HỆ THỐNG TRẢ THƯỞNG CỘNG ĐỒNG (WEB3 BOUNTY SYSTEM)](#7-module-6-cơ-chế-kinh-tế-token--hệ-thống-trả-thưởng-cộng-đồng-web3-bounty-system)
   - [7.1. Kiến thức cốt lõi (Core Concepts)](#71-kiến-thức-cốt-lõi-core-concepts)
   - [7.2. Kỹ năng thực hành (Practical Skills)](#72-kỹ-năng-thực-hành-practical-skills)
   - [7.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)](#73-giáo-trình-nghiên-cứu--sách-kinh-điển-research-papers--books)
   - [7.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)](#74-tiêu-chuẩn-và-đặc-tả-kỹ-thuật-official-standards--specs)
   - [7.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)](#75-dự-án-mã-nguồn-mở-tham-khảo-open-source-reference-repositories)
8. [LỘ TRÌNH HỌC TẬP CÓ CẤU TRÚC 12 TUẦN (12-WEEK STRUCTURED ROADMAP)](#8-lộ-trình-học-tập-có-cấu-trúc-12-tuần-12-week-structured-roadmap)
   - [8.1. Chặng 1 (Tuần 1 - 3): Nền tảng Multi-Agent & Kỹ thuật Dữ liệu Pháp luật Việt Nam](#81-chặng-1-tuần-1---3-nền-tảng-multi-agent--kỹ-thuật-dữ-liệu-pháp-luật-việt-nam)
   - [8.2. Chặng 2 (Tuần 4 - 6): Advanced Legal RAG, Hybrid Retrieval & Thẩm định Ảo giác](#82-chặng-2-tuần-4---6-advanced-legal-rag-hybrid-retrieval--thẩm-định-ảo-giác)
   - [8.3. Chặng 3 (Tuần 7 - 9): Web3 Fullstack, Smart Contract Foundry, x402 & ERC-8004](#83-chặng-3-tuần-7---9-web3-fullstack-smart-contract-foundry-x402--erc-8004)
   - [8.4. Chặng 4 (Tuần 10 - 12): Merkle Provenance Rollup, Sàn thưởng Bounty & Production Hardening](#84-chặng-4-tuần-10---12-merkle-provenance-rollup-sàn-thưởng-bounty--production-hardening)
9. [DỰ ÁN THỰC HÀNH MẪU (CAPSTONE PROJECTS)](#9-dự-án-thực-hành-mẫu-capstone-projects)
   - [9.1. Capstone 1: Multi-Agent Legal Dispatcher với LangGraph & Bộ bóc tách Luật phân cấp](#91-capstone-1-multi-agent-legal-dispatcher-với-langgraph--bộ-bóc-tách-luật-phân-cấp)
   - [9.2. Capstone 2: Động cơ Hybrid Legal RAG Đa miền với BGE-Reranker & NLI Guardrail](#92-capstone-2-động-cơ-hybrid-legal-rag-đa-miền-với-bge-reranker--nli-guardrail)
   - [9.3. Capstone 3: Cổng thanh toán vi mô x402 (EIP-3009 USDC) & Sổ cái ERC-8004 trên L2](#93-capstone-3-cổng-thanh-toán-vi-mô-x402-eip-3009-usdc--sổ-cái-erc-8004-trên-l2)
   - [9.4. Capstone 4: Nền tảng Trust-AGENT Hoàn chỉnh: Merkle Rollup & Hệ thống Escrow Bounty](#94-capstone-4-nền-tảng-trust-agent-hoàn-chỉnh-merkle-rollup--hệ-thống-escrow-bounty)
10. [PHỤ LỤC TÀI NGUYÊN, CÔNG CỤ VÀ TIÊU CHUẨN ĐÁNH GIÁ (APPENDIX & TOOLING)](#10-phụ-lục-tài-nguyên-công-cụ-và-tiêu-chuẩn-đánh-giá-appendix--tooling)

---

## 1. TỔNG QUAN VÀ KHUNG NĂNG LỰC CỐT LÕI (OVERVIEW & COMPETENCY FRAMEWORK)

### 1.1. Bối cảnh kỹ thuật và Khoảng cách năng lực cần lấp đầy

Báo cáo Phân tích Khoảng trống (`docs/GAP_ANALYSIS.md`) đã chỉ rõ rằng dự án **Trust-AGENT** hiện tại đang ở giai đoạn nguyên mẫu ban đầu (MVP) với nhiều giới hạn kỹ thuật cần được giải quyết một cách có hệ thống:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        KHOẢNG TRỐNG NĂNG LỰC HIỆN TRẠNG (GAP STATE)                    │
├─────────────────────────────────────────┬──────────────────────────────────────────────┤
│ Lĩnh vực AI & NLP Pháp lý                │ Lĩnh vực Web3 & Agentic Commerce             │
├─────────────────────────────────────────┼──────────────────────────────────────────────┤
│ 1. Router Stateless, thiếu bộ nhớ phiên │ 1. Hạ tầng thanh toán x402 đạt 0% (Greenfield)│
│ 2. Tổng hợp kết quả bằng nối chuỗi thô  │ 2. Chưa có Smart Contract ERC-8004 Identity  │
│ 3. Sai lệch dữ liệu Thuế (100% Kế toán) │ 3. Băm cục bộ 24 ký tự, chưa có Merkle Proof │
│ 4. Thiếu Cross-Encoder Reranker         │ 4. Chưa có cơ chế Staking/Escrow Bounty Pool │
│ 5. Thiếu NLI Hallucination Cross-check  │ 5. Chưa có cơ chế bảo vệ sự riêng tư (Salt)  │
└─────────────────────────────────────────┴──────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        MỤC TIÊU NĂNG LỰC TOÀN DIỆN (TARGET PROFILE)                    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Kỹ sư có khả năng làm chủ cả 2 thế giới: Hệ thống Multi-Agent AI hiệu năng cao         │
│ và Kiến trúc Hợp đồng thông minh phân tán Web3 trên mạng máy ảo Ethereum (EVM).        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

Tài liệu này được biên soạn như một **Giáo trình Kỹ thuật Chuẩn mực (Master Curriculum)** nhằm cung cấp cho kỹ sư con đường ngắn nhất, bài bản nhất và thực chiến nhất để làm chủ toàn bộ ngăn xếp công nghệ của hệ thống Trust-AGENT.

---

### 1.2. Ma trận năng lực chữ T (T-Shaped Competency Matrix)

Một kỹ sư nòng cốt trong dự án Trust-AGENT cần phát triển mô hình năng lực chữ T với chiều rộng bao quát toàn bộ quy trình tích hợp AI - Web3 và chiều sâu chuyên sâu tại ít nhất 2 trong 6 phân hệ trụ cột:

```
                     CHIỀU RỘNG: TỔNG QUAN KIẾN TRÚC & HỆ SINH THÁI
 ┌────────────────────────────────────────────────────────────────────────────────────┐
 │  Python 3.11+ │ FastAPI │ Docker │ Git/CI-CD │ REST/JSON-RPC │ EVM Basics │ Linux  │
 └────────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────────────────┐
 │                        CHIỀU SÂU CHUYÊN MÔN (DEEP EXPERTISE)                       │
 ├──────────────────┬──────────────────┬──────────────────┬───────────────────────────┤
 │  Multi-Agent &   │  Advanced Legal  │ x402 Micropay &  │  Provenance, Merkle &     │
 │  Orchestration   │  RAG Systems     │ ERC-8004 (EVM)   │  Game-Theoretic Bounties  │
 ├──────────────────┼──────────────────┼──────────────────┼───────────────────────────┤
 │ • LangGraph DAG  │ • VN Law Parsing │ • EIP-712 / 3009 │ • Merkle Proof & MMR      │
 │ • ReAct Patterns │ • Hybrid (BM25+) │ • Foundry/Forge  │ • Salted Commitments      │
 │ • Session Memory │ • Cross-Encoder  │ • USDC Flows L2  │ • Escrow & Staking/Slash  │
 │ • Blackboard Com │ • NLI Entailment │ • Smart Security │ • Kleros Dispute Arb      │
 └──────────────────┴──────────────────┴──────────────────┴───────────────────────────┘
```

---

### 1.3. Yêu cầu tiên quyết (Prerequisites)

Để tiếp thu tối ưu lộ trình học tập, kỹ sư cần trang bị nền tảng sau:

1. **Ngôn ngữ lập trình**:
   - **Python (Thượng thừa)**: Lập trình bất đồng bộ (`asyncio`), gõ tĩnh (`typing`, `Pydantic v2`), mô hình dữ liệu trừu tượng, kiến trúc đa luồng.
   - **Solidity (Trung cấp -> Cao cấp)**: Cú pháp 0.8.20+, hiểu sâu EVM storage layout, memory vs calldata, custom errors, và opcodes mới (EIP-1153 `TSTORE`/`TLOAD`).
   - **Shell / Tooling**: Bash, PowerShell, Git, Docker & Docker Compose.

2. **Toán học & Mật mã học cơ sở**:
   - Đại số tuyến tính & Xác suất: Vector embeddings, cosine similarity, rank fusion scoring.
   - Mật mã học ứng dụng: Hàm băm mật mã (SHA-256, Keccak-256), Cấu trúc dữ liệu hình cây (Merkle Tree, Patricia Trie), Chữ ký số đường cong elliptic (ECDSA secp256k1).

3. **Kiến thức Pháp luật Đại cương**:
   - Hiểu biết cơ bản về thể chế văn bản quy phạm pháp luật Việt Nam theo Luật Ban hành VBQPPL (Luật, Nghị định, Thông tư) và nguyên tắc thứ bậc hiệu lực pháp lý.

---

## 2. MODULE 1: HỆ THỐNG MULTI-AGENT & KỸ THUẬT ĐIỀU PHỐI (MULTI-AGENT ORCHESTRATION)

### 2.1. Kiến thức cốt lõi (Core Concepts)

#### 2.1.1. LangGraph StateGraph Architecture
- **StateGraph**: Mô hình điều phối tính toán dựa trên đồ thị trạng thái có hướng, hỗ trợ chu trình lặp (cyclic) thay vì chỉ DAG thuần túy.
- **State & Reducers**: Quản lý trạng thái chia sẻ (Shared State) thông qua Pydantic hoặc `TypedDict`. Sử dụng Reducer (như `operator.add` hoặc custom reducer) để giải quyết xung đột khi nhiều agent cùng ghi dữ liệu đồng thời (parallel branch execution).
- **Conditional Edges**: Cơ chế định tuyến động dựa trên logic kiểm tra trạng thái đầu ra của nút trước đó (`should_continue`, `route_to_domain`).

#### 2.1.2. ReAct Agent Loop (Reasoning + Acting)
- Vòng lặp suy luận lồng ghép hành động:
  $$\text{Query} \xrightarrow{} \text{Thought (Suy ngẫm)} \xrightarrow{} \text{Action (Gọi công cụ)} \xrightarrow{} \text{Observation (Nhận kết quả)} \xrightarrow{} \dots \xrightarrow{} \text{Final Answer}$$
- Kiểm soát dừng (Stop criteria) và giới hạn vòng lặp (max iterations) để ngăn chặn vòng lặp vô tận (infinite loops) làm cạn kiệt token/ngân sách.

#### 2.1.3. Master Router & Dispatcher Patterns
- **Semantic Intent Classification**: Nhận diện ý định đa tầng (Multi-intent) của người dùng từ văn bản tự nhiên bằng LLM Structured Output (`with_structured_output`) kết hợp Keyword Fallback.
- **Parallel Fan-out / Fan-in (`Send` API)**: Phát tán đồng thời các nhánh truy vấn con cho từng agent chuyên biệt (Giao thông, Lao động, Thuế) và gom tụ kết quả tại nút Synthesizer.

#### 2.1.4. Stateful Dialog Memory & Checkpointing
- Khắc phục nhược điểm Stateless của hệ thống hiện tại.
- **Checkpointers (`PostgresSaver`, `RedisSaver`)**: Lưu trữ toàn bộ snapshot đồ thị tại từng bước tính toán. Cho phép khôi phục phiên hội thoại qua `thread_id`, hỗ trợ tua lại thời gian (time-travel debugging) và can thiệp của con người (Human-in-the-loop).
- Quản trị cửa sổ ngữ cảnh: Tóm tắt ngữ cảnh tự động (Conversation Summary Buffer) khi số lượng tokens vượt quá ngưỡng 4.000 tokens.

#### 2.1.5. Semantic Query Decomposition DAG
- Kỹ thuật phân rã câu hỏi liên ngành phức tạp (ví dụ: *"Doanh nghiệp vận tải bị phạt chở quá tải thì chi phí phạt đó có được trừ vào thuế TNDN và có được trừ lương tài xế không?"*).
- Tạo DAG phụ thuộc:
  ```
                         [Câu hỏi đa ngành phức tạp]
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
       [Nhánh 1: Vi phạm quá tải]      [Nhánh 2: Khấu trừ lương]
          (Traffic Legal Agent)           (Labor Legal Agent)
                     │                               │
                     └───────────────┬───────────────┘
                                     ▼
                      [Nhánh 3: Chi phí Thuế TNDN]
                           (Tax Legal Agent)
                                     │
                                     ▼
                       [Legal Synthesis Engine]
  ```

#### 2.1.6. Inter-Agent Message Protocol & Blackboard Pattern
- **Giao thức thông điệp chuẩn (A2A Message Envelope)**: Định dạng trao đổi giữa các agent với metadata định danh:
  ```json
  {
    "trace_id": "uuid-v4",
    "parent_id": "dispatcher_01",
    "sender": "tax_agent",
    "recipient": "synthesizer",
    "domain": "tax",
    "payload": {
      "sub_query": "Chi phí phạt giao thông có được tính chi phí được trừ thuế TNDN?",
      "findings": "Không được trừ theo Điểm 2.36 Khoản 2 Điều 6 Thông tư 78/2014/TT-BTC",
      "citations": ["TT_78_2014_BTC_D6_K2_P2_36"],
      "confidence": 0.96
    }
  }
  ```
- **Blackboard Pattern**: Không gian bộ nhớ chia sẻ toàn cục (Global Scratchpad) nơi các chuyên gia pháp lý đăng ký bằng chứng và phát hiện trung gian. Agent thẩm định chéo (Cross-checker) quan sát bảng tin này để phát hiện mâu thuẫn giữa các quy định của ngành khác nhau.

---

### 2.2. Kỹ năng thực hành (Practical Skills)

1. Thiết kế và triển khai `StateGraph` phức tạp trên LangGraph với đầy đủ nút phân loại, rẽ nhánh song song, gom tụ và xác thực.
2. Cấu hình `PostgresSaver` kết nối cơ sở dữ liệu PostgreSQL để lưu trữ phiên hội thoại đa lượt có tính bền bỉ (persistence).
3. Viết Pydantic Schemas bắt buộc LLM trả về cấu trúc phân tách truy vấn theo chuẩn JSON Schema nghiêm ngặt.
4. Xây dựng cơ chế xử lý lỗi ngoại lệ (Fallback & Retry with Exponential Backoff) khi một Sub-Agent chuyên ngành gặp sự cố hoặc timeout.

---

### 2.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)

1. **ReAct: Synergizing Reasoning and Acting in Language Models**  
   - *Tác giả*: Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao.  
   - *Hội nghị*: ICLR 2023.  
   - *ArXiv*: [arXiv:2210.03629](https://arxiv.org/abs/2210.03629).  
   - *Giá trị cốt lõi*: Nền tảng phương pháp luận cho việc kết hợp sinh chuỗi suy luận (Chain of Thought) và hành động tương tác với công cụ bên ngoài.

2. **Communicative Agents for Software Development (ChatDev)**  
   - *Tác giả*: Chen Qian et al.  
   - *Hội nghị*: ACL 2024.  
   - *ArXiv*: [arXiv:2307.07924](https://arxiv.org/abs/2307.07924).  
   - *Giá trị cốt lõi*: Kiến trúc giao tiếp đa tác tử dựa trên mô hình phân vai (Role-playing) và giao thức đồng thuận theo pha (Chat-based consensus).

3. **Sách: Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations**  
   - *Tác giả*: Yoav Shoham, Kevin Leyton-Brown.  
   - *Nhà xuất bản*: Cambridge University Press (2008).  
   - *Giá trị cốt lõi*: Giáo trình toán học kinh điển về hệ thống đa tác tử, lý thuyết truyền tin và phối hợp hành động phân tán.

4. **Sách: Designing Autonomous AI Agents: Principles, Patterns, and Architecture**  
   - *Tác giả*: Mark Nelson.  
   - *Nhà xuất bản*: Packt Publishing (2024).  
   - *Giá trị cốt lõi*: Các mẫu kiến trúc thực tế (Router, Supervisor, Plan-and-Solve, Blackboard) áp dụng cho LLM agents.

---

### 2.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)

- **LangGraph Architecture Specification (v0.2+)**: [LangGraph Docs](https://langchain-ai.github.io/langgraph/).
- **FIPA ACL Message Structure Specification (SC00061G)**: Đặc tả của Tổ chức các Tác tử Vật lý Thông minh về cấu trúc thông điệp trao đổi giữa các agent tự trị.
- **OpenTelemetry Semantic Conventions for Generative AI Systems**: Chuẩn hóa việc ghi nhận vết (tracing span) cho chuỗi gọi agent và công cụ.

---

### 2.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)

- [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph): Thư viện mã nguồn mở tiêu chuẩn xây dựng đồ thị tác tử chu trình có trạng thái.
- [microsoft/autogen](https://github.com/microsoft/autogen): Khung điều phối hội thoại đa tác tử của Microsoft Research.
- [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI): Framework lập trình tác tử phân vai trực quan, tối ưu cho quy trình tự động hóa tác vụ.

---

## 3. MODULE 2: ADVANCED LEGAL RAG CHO VĂN BẢN QUY PHẠM PHÁP LUẬT VIỆT NAM

### 3.1. Kiến thức cốt lõi (Core Concepts)

#### 3.1.1. Thứ bậc Hiệu lực và Cấu trúc Văn bản Quy phạm Pháp luật Việt Nam
Tuân thủ Luật Ban hành văn bản quy phạm pháp luật (Luật số 80/2015/QH13 và Luật sửa đổi số 63/2020/QH14):
1. **Hiến pháp**: Có hiệu lực pháp lý cao nhất.
2. **Bộ luật, Luật**: Do Quốc hội ban hành.
3. **Nghị quyết của Quốc hội**.
4. **Pháp lệnh, Nghị quyết của Ủy ban Thường vụ Quốc hội**.
5. **Nghị định của Chính phủ**: Quy định chi tiết điều, khoản được giao trong luật.
6. **Quyết định của Thủ tướng Chính phủ**.
7. **Thông tư của Bộ trưởng, Thủ trưởng cơ quan ngang bộ**: Hướng dẫn thi hành Nghị định.

*Nguyên tắc áp dụng*: Văn bản có hiệu lực pháp lý cao hơn có giá trị ưu tiên. Trong trường hợp các văn bản cùng cấp quy định khác nhau về cùng một vấn đề thì áp dụng văn bản ban hành sau.

```
       CẤU TRÚC PHÂN CẤP NỘI TẠI CỦA MỘT VĂN BẢN QUY PHẠM PHÁP LUẬT
┌────────────────────────────────────────────────────────────────────────┐
│ PHẦN (Part) / CHƯƠNG (Chapter) / MỤC (Section)                         │
│  └─► ĐIỀU (Article)                                                    │
│        └─► KHOẢN (Clause)                                              │
│              └─► ĐIỂM (Point)                                          │
│                    └─► TIẾT (Item)                                     │
└────────────────────────────────────────────────────────────────────────┘
```

#### 3.1.2. Hierarchical Legal Chunking (Bóc tách văn bản bảo toàn ngữ cảnh)
- **Sai lầm phổ biến**: Cắt văn bản theo kích thước cố định (fixed token size, ví dụ: 500 tokens có 50 tokens overlap). Điều này làm xé nát nội dung Khoản/Điểm, làm mất ngữ cảnh của Điều và Tên Luật dẫn đến LLM suy luận sai lệch hoàn toàn.
- **Giải pháp Chuẩn mực**: Bóc tách theo cây cú pháp pháp lý (Legal AST):
  - Mỗi chunk là một **Khoản** (Clause) hoặc một **Điều** (Article) độc lập.
  - Mỗi chunk bắt buộc phải được gắn tiếp đầu ngữ ngữ cảnh phân cấp (Hierarchical Breadcrumb Header):
    ```markdown
    [VĂN BẢN]: Luật Trật tự, an toàn giao thông đường bộ 2024 (Luật số 36/2024/QH15)
    [CHƯƠNG]: Chương II: Quy tắc giao thông đường bộ
    [ĐIỀU]: Điều 9: Chấp hành hệ thống báo hiệu đường bộ
    [KHOẢN]: Khoản 2
    [NỘI DUNG]: Người tham gia giao thông đường bộ phải chấp hành hiệu lệnh và chỉ dẫn...
    ```

#### 3.1.3. Kiến trúc Tìm kiếm Lai (Hybrid Search Architecture)
Kết hợp hai trường phái bổ trợ lẫn nhau:
1. **Tìm kiếm Ngữ nghĩa Sâu (Dense Vector Retrieval)**:
   - Dùng mô hình nhúng đa ngôn ngữ hiện đại: `BAAI/bge-m3` (hỗ trợ 1024 chiều, hiểu ngữ nghĩa đa tầng) hoặc `intfloat/multilingual-e5-large`.
   - Bắt trọn ý định tìm kiếm tương đồng khái niệm dù câu hỏi người dùng không dùng từ ngữ giống hệt văn bản luật.
2. **Tìm kiếm Từ khóa Chính xác (Sparse Lexical Retrieval - BM25Okapi / BM25Plus)**:
   - Cần kíp cho văn bản pháp luật vì chứa các thuật ngữ pháp lý cố định ("tước quyền sử dụng giấy phép lái xe", "khấu trừ 10% tại nguồn", "hành vi bị nghiêm cấm").
   - **Tách từ tiếng Việt chuyên biệt (Vietnamese Word Segmentation)**: Phải sử dụng bộ tách từ như `underthesea` hoặc `pyvi` để chuyển đổi:
     `"tước giấy phép lái xe"` $\xrightarrow{}$ `["tước", "giấy_phép_lái_xe"]` thay vì tách rời từng âm tiết rời rạc gây nhiễu điểm BM25.

#### 3.1.4. Thuật toán Hợp nhất Thứ hạng Tuyển chọn (Reciprocal Rank Fusion - RRF)
- Công thức hợp nhất thứ tự xếp hạng không cần chuẩn hóa thang điểm:
  $$RRF_{score}(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$
  Trong đó:
  - $M$: Tập hợp các bộ tìm kiếm (Dense + Sparse).
  - $r_m(d)$: Thứ hạng (rank, 1-indexed) của tài liệu $d$ trong bộ tìm kiếm $m$.
  - $k$: Hằng số làm mượt (Smoothing parameter), thực nghiệm quốc tế và chuẩn công nghiệp chọn $k = 60$.

#### 3.1.5. Tái xếp hạng bằng Cross-Encoder (Cross-Encoder Reranking)
- Bi-encoder (Vector search) mã hóa Query và Document độc lập $\xrightarrow{}$ Tốc độ cao nhưng mất tương tác token chéo.
- Cross-Encoder nhận đầu vào là cặp `[Query, Document]` cùng lúc vào Transformer layer, tính toán ma trận Attention toàn diện $\xrightarrow{}$ Cho điểm số tương quan chính xác vượt trội.
- Mô hình khuyến nghị: `BAAI/bge-reranker-v2-m3` hoặc `BAAI/bge-reranker-large`.
- Pipeline xử lý: Top-50 kết quả từ RRF $\xrightarrow{}$ Đưa qua Cross-Encoder $\xrightarrow{}$ Chọn Top-5 tài liệu chất lượng nhất đưa vào Prompt của LLM.

#### 3.1.6. Kiểm soát Ảo giác bằng Suy luận Ngôn ngữ Tự nhiên (NLI Entailment Verification)
- Thay vì tin tưởng mù quáng vào câu trả lời của LLM, hệ thống sử dụng mô hình NLI (Natural Language Inference) làm chốt chặn:
  - **Tiền đề (Premise)**: Trích đoạn Điều/Khoản luật thực tế được tìm thấy.
  - **Giả thuyết (Hypothesis)**: Từng câu khẳng định trong câu trả lời sinh ra bởi Agent.
  - Phân loại logic 3 nhãn:
    - $\text{Entailment}$ (Kéo theo / Phù hợp): Tuyên bố được chứng minh bởi luật $\xrightarrow{}$ Được duyệt.
    - $\text{Contradiction}$ (Mâu thuẫn): Tuyên bố trái ngược với luật $\xrightarrow{}$ Bác bỏ ngay lập tức, cảnh báo vi phạm.
    - $\text{Neutral}$ (Trung lập / Không có căn cứ): Tuyên bố suy diễn vô căn cứ $\xrightarrow{}$ Đánh dấu thiếu bằng chứng.

#### 3.1.7. Lọc Metadata Hiệu lực Thời gian (Temporal Metadata Filtering)
- Khắc phục khoảng trống lớn trong cơ sở dữ liệu hiện tại (100% bản ghi thiếu metadata thời gian).
- Mỗi văn bản pháp luật và từng chunk phải có các trường:
  - `effective_from` (Ngày có hiệu lực): e.g. `2025-01-01`.
  - `expiry_date` (Ngày hết hiệu lực): `null` nếu còn hiệu lực.
  - `status`: `active` (đang có hiệu lực), `expired` (hết hiệu lực), `amended` (được sửa đổi/bổ sung).
- Truy vấn RAG phải tự động áp dụng bộ lọc: $\text{effective\_from} \le \text{query\_date} \land (\text{expiry\_date} \text{ IS NULL} \lor \text{expiry\_date} > \text{query\_date})$.

---

### 3.2. Kỹ năng thực hành (Practical Skills)

1. Xây dựng Parser bóc tách tự động cấu trúc Chương/Điều/Khoản/Điểm từ định dạng HTML/Docx của văn bản pháp luật Việt Nam.
2. Cài đặt thuật toán RRF kết hợp BM25 (với bộ tokenizer tiếng Việt `underthesea`) và Vectorstore ChromaDB.
3. Tích hợp và tối ưu hóa suy luận Cross-Encoder `bge-reranker-v2-m3` bằng ONNX Runtime hoặc vLLM để đạt độ trễ $< 150\text{ms}$.
4. Viết module NLI Guardrail kiểm tra tính logic của câu trả lời trước khi trả về cho khách hàng.

---

### 3.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)

1. **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks**  
   - *Tác giả*: Patrick Lewis et al. (Facebook AI Research / UCL / NYU).  
   - *Hội nghị*: NeurIPS 2020.  
   - *ArXiv*: [arXiv:2005.11401](https://arxiv.org/abs/2005.11401).  
   - *Giá trị cốt lõi*: Bài báo nền tảng khai sinh kiến trúc RAG hiện đại.

2. **Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods**  
   - *Tác giả*: Gordon V. Cormack, Charles L. A. Clarke, Stefan Büttcher.  
   - *Hội nghị*: ACM SIGIR 2009.  
   - *Giá trị cốt lõi*: Định nghĩa toán học và bằng chứng thực nghiệm của giải thuật RRF.

3. **BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation**  
   - *Tác giả*: Jianlv Chen et al. (BAAI).  
   - *Năm*: 2024.  
   - *ArXiv*: [arXiv:2402.03216](https://arxiv.org/abs/2402.03216).  
   - *Giá trị cốt lõi*: Kiến trúc embedding đa ngôn ngữ hỗ trợ cả dense, sparse và multi-vector retrieval.

4. **LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning in Large Language Models**  
   - *Tác giả*: Neel Guha et al. (Stanford University).  
   - *Hội nghị*: NeurIPS 2023.  
   - *ArXiv*: [arXiv:2308.11462](https://arxiv.org/abs/2308.11462).  
   - *Giá trị cốt lõi*: Bộ chuẩn đánh giá khả năng suy luận pháp lý và trích dẫn điều khoản cho mô hình ngôn ngữ lớn.

---

### 3.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)

- **Luật Ban hành văn bản quy phạm pháp luật Việt Nam (Luật số 80/2015/QH13 và Luật số 63/2020/QH14)**.
- **Nghị định số 34/2016/NĐ-CP và Nghị định số 154/2020/NĐ-CP**: Quy chuẩn kỹ thuật trình bày, thể thức văn bản quy phạm pháp luật (Chương, Điều, Khoản, Điểm).
- **BM25Okapi Formulation Standard**: Stephen Robertson and Karen Spärck Jones (Okapi BM25 Specification).

---

### 3.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)

- [FlagOpen/FlagEmbedding](https://github.com/FlagOpen/FlagEmbedding): Kho mã nguồn mở chính thức của BAAI chứa mô hình BGE-M3 và BGE-Reranker.
- [chroma-core/chroma](https://github.com/chroma-core/chroma): Vector database mã nguồn mở nhúng, hỗ trợ lưu trữ metadata đa tầng.
- [underthesea/underthesea](https://github.com/underthesea/underthesea): Bộ công cụ xử lý ngôn ngữ tự nhiên tiếng Việt (Word segmentation, POS tagging, NER).
- [dorianbrown/rank_bm25](https://github.com/dorianbrown/rank_bm25): Thư viện triển khai các giải thuật BM25Okapi, BM25L, BM25+ tối ưu bằng Python.

---

## 4. MODULE 3: GIAO THỨC THANH TOÁN X402 & KINH TẾ TÁC TỬ (AGENTIC COMMERCE)

### 4.1. Kiến thức cốt lõi (Core Concepts)

#### 4.1.1. Mã trạng thái HTTP 402 Payment Required & Chuẩn x402
- **Lịch sử**: HTTP 402 được định nghĩa trong RFC 7231 / RFC 9110 dành riêng cho các cơ chế thanh toán số trong tương lai nhưng bị bỏ quên suốt 3 thập kỷ.
- **Giao thức x402 (x402 Protocol)**: Tiêu chuẩn hóa luồng giao tiếp giữa Khách hàng (Agent / Client) và Máy chủ dịch vụ (Service Provider):

```
[Agent / Client]                                           [Trust-AGENT API Gateway]
       │                                                               │
       │─── 1. POST /api/v1/query (Kèm câu hỏi pháp lý) ──────────────►│
       │                                                               │ (Kiểm tra thanh toán)
       │◄── 2. HTTP 402 Payment Required ──────────────────────────────│
       │       Header: WWW-Authenticate: x402                          │ (Tạo payment challenge)
       │       Body: {                                                 │
       │         "network": "base",                                    │
       │         "token": "USDC",                                      │
       │         "price": "0.01",                                      │
       │         "recipient": "0xAgentVault...",                       │
       │         "nonce": "0xabc123...",                               │
       │         "deadline": 1735689600                                │
       │       }                                                       │
       │                                                               │
       │ (Agent ký số EIP-712 EIP-3009 ngoại tuyến)                    │
       │                                                               │
       │─── 3. POST /api/v1/query ─────────────────────────────────────►│
       │       Header: Authorization: x402 <signature_payload>          │
       │       Body: { ... query ... }                                 │ (Facilitator xác thực ký số)
       │                                                               │ (Settlement hoặc nhả data)
       │◄── 4. HTTP 200 OK ────────────────────────────────────────────│
       │       Body: {                                                 │
       │         "answer": "Theo Khoản 1 Điều ...",                    │
       │         "citations": [...],                                   │
       │         "receipt": "0xProofReceiptHash..."                    │
       │       }                                                       │
```

#### 4.1.2. Ký dữ liệu có cấu trúc EIP-712 (Typed Structured Data Hashing and Signing)
- Thay vì ký một chuỗi bytecode mờ ám (dễ bị tấn công lừa đảo đảo chữ ký), EIP-712 yêu cầu hiển thị và băm cấu trúc dữ liệu rõ ràng.
- **Domain Separator**: Ngăn chặn tấn công phát lại chữ ký (Replay Attack) giữa các ứng dụng và các mạng khác nhau:
  $$\text{DomainSeparator} = \text{keccak256}(\text{abi.encode}(\text{TypeHash}, \text{nameHash}, \text{versionHash}, \text{chainId}, \text{verifyingContract}))$$
- **Struct Hash**:
  $$\text{StructHash} = \text{keccak256}(\text{abi.encode}(\text{TypeHash}, \text{params}\dots))$$

#### 4.1.3. Chuẩn Ủy quyền Chuyển tiền Không tốn Gas EIP-3009 (Transfer With Authorization)
- Được triển khai trên hợp đồng thông minh của đồng tiền ổn định USDC (Circle FiatTokenV2).
- Phương thức `transferWithAuthorization`:
  ```solidity
  function transferWithAuthorization(
      address from,
      address to,
      uint256 value,
      uint256 validAfter,
      uint256 validBefore,
      bytes32 nonce,
      uint8 v,
      bytes32 r,
      bytes32 s
  ) external;
  ```
- **Ưu thế vượt trội**: Người dùng / Agent chỉ cần ký ngoại tuyến (Off-chain signature) mà **không cần sở hữu đồng tiền cơ sở (như ETH) để trả phí gas**. Máy chủ dịch vụ (Facilitator) hoặc Trạm chuyển tiếp (Relayer) sẽ gửi giao dịch lên chuỗi và chịu phí gas nhỏ lẻ (vốn được bù đắp bởi giá dịch vụ).

#### 4.1.4. Hạ tầng Layer-2 EVM (Base & Arbitrum)
- Thanh toán vi mô (Micropayments $0.001 - $0.05) bất khả thi trên Ethereum L1 vì phí gas từ $1.00 - $20.00.
- Layer-2 Optimistic Rollup (Base, Arbitrum): Tận dụng EIP-4844 Blob Data giúp giảm phí gas mỗi giao dịch xuống mức $< 0.001\$$, làm cho mô hình "trả tiền theo từng câu hỏi" (Pay-per-query) trở nên hoàn toàn khả thi về mặt kinh tế.

#### 4.1.5. State Channels & Ticket Session Allowance
- Đối với khách hàng thực hiện hàng trăm truy vấn trong một phiên (Session):
  - Người dùng ký một ủy quyền hạn mức phiên (Session Allowance, e.g. 2.00 USDC).
  - Từng câu hỏi sẽ trừ dần phiếu vé (Ticket) off-chain.
  - Khi kết thúc phiên hoặc hết hạn mức, hệ thống mới gửi 1 giao dịch quyết toán (Settlement transaction) duy nhất lên mạng L2.

---

### 4.2. Kỹ năng thực hành (Practical Skills)

1. Xây dựng Middleware trên FastAPI chặn yêu cầu và phát mã lỗi HTTP 402 kèm EIP-712 challenge schema.
2. Lập trình Client bằng Python (`web3.py` / `eth_account`) và TypeScript (`viem`) thực hiện ký số EIP-712 EIP-3009.
3. Tích hợp Facilitator Server tương tác với Smart Contract USDC trên mạng Base Sepolia để thực hiện rút tiền thông qua `receiveWithAuthorization`.
4. Quản lý Nonce và Deadlines để ngăn ngừa hoàn toàn các lỗ hổng Replay Attack trong thanh toán vi mô.

---

### 4.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)

1. **x402: An Open Standard for Internet Micropayments**  
   - *Tổ chức*: x402 Foundation & Coinbase Developer Platform (2024).  
   - *Tài liệu*: [x402.org Documentation](https://x402.org).  
   - *Giá trị cốt lõi*: Toàn văn kiến trúc giao thức x402 chuẩn hóa cho nền kinh tế tác tử tự trị (Agentic Economy).

2. **Simple Fast Payments Using State Channels**  
   - *Tác giả*: Stefan Dziembowski, Sebastian Faust, Kristina Hostáková.  
   - *Hội nghị*: ACM CCS 2018.  
   - *Giá trị cốt lõi*: Mô hình kênh thanh toán ngoài chuỗi bảo đảm an toàn bằng chứng cứ mật mã.

3. **Sách: Mastering Ethereum: Building Smart Contracts and DApps**  
   - *Tác giả*: Andreas M. Antonopoulos, Gavin Wood.  
   - *Nhà xuất bản*: O'Reilly Media (2018).  
   - *Giá trị cốt lõi*: Giáo trình chuẩn mực về mật mã học Ethereum, cấu trúc giao dịch và máy ảo EVM.

---

### 4.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)

- **RFC 9110: HTTP Semantics — Section 15.5.3 (Status Code 402 Payment Required)**.
- **EIP-712: Ethereum typed structured data hashing and signing**: [eips.ethereum.org/EIPS/eip-712](https://eips.ethereum.org/EIPS/eip-712).
- **EIP-3009: Transfer With Authorization**: [eips.ethereum.org/EIPS/eip-3009](https://eips.ethereum.org/EIPS/eip-3009).
- **Circle USDC FiatTokenV2_2 Smart Contract Specification**: Đặc tả chính thức triển khai EIP-3009 và EIP-2612.

---

### 4.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)

- [coinbase/x402](https://github.com/coinbase/x402): Kho mã nguồn mở giao thức x402 của Coinbase Developer Platform.
- [circlefin/stablecoin-evm](https://github.com/circlefin/stablecoin-evm): Hợp đồng thông minh EVM chính thức của USDC triển khai EIP-3009 `transferWithAuthorization`.
- [wevm/viem](https://github.com/wevm/viem): Thư viện TypeScript gọn nhẹ, hiệu năng cao cho EVM hỗ trợ hoàn hảo EIP-712.
- [ethereum/web3.py](https://github.com/ethereum/web3.py): Thư viện Python chính thống tương tác với mạng Ethereum.

---

## 5. MODULE 4: CHUẨN ERC-8004 & PHÁT TRIỂN SMART CONTRACT TRÊN EVM

### 5.1. Kiến thức cốt lõi (Core Concepts)

#### 5.1.1. Khái niệm Agent Identity (Định danh Tác tử Tự trị trên On-Chain)
- Trong mô hình kinh tế Web3, tác tử AI không chỉ là một tiến trình phần mềm mà là một thực thể kinh tế tự trị có định danh (On-chain Identity):
  - Sở hữu địa chỉ ví hoặc Hợp đồng Tài khoản Thông minh (Smart Contract Account - ERC-4337).
  - Có hồ sơ năng lực công khai, cho phép người dùng và các tác tử khác phát hiện và gọi dịch vụ tự động.

#### 5.1.2. Khai báo Agent Capability & Policy Hashing
- Ánh xạ trực tiếp từ `DomainAgentSpec` trong mã nguồn sang hợp đồng thông minh:
  ```solidity
  struct AgentProfile {
      uint256 agentId;
      address owner;
      string domain;          // "traffic", "labor", "tax"
      string metadataURI;     // ipfs://... (Mô tả chi tiết năng lực, phiên bản model)
      bytes32 capabilityHash; // keccak256(tools + schemas + SLA)
      bytes32 policyHash;     // keccak256(cam kết tuân thủ quy tắc trích dẫn)
      uint256 registeredAt;
      bool isActive;
  }
  ```
- **Policy Hash**: Bằng chứng mật mã chứng minh agent cam kết tuân thủ nguyên tắc không ảo giác, chỉ trích dẫn các điều luật có hiệu lực. Nếu vi phạm, policy hash này sẽ là bằng chứng chống lại agent trong các phiên phân xử.

#### 5.1.3. Sổ cái Uy tín On-Chain (On-Chain Reputation Ledger)
- Ghi nhận hiệu năng thực thi bất biến:
  - Tổng số truy vấn đã xử lý (`totalQueries`).
  - Số truy vấn trích dẫn chính xác được hệ thống xác thực (`verifiedQueries`).
  - Số truy vấn bị khiếu nại hoặc bắt lỗi sai luật (`disputedQueries`).
  - Điểm uy tín chuẩn hóa (Reputation Score $\in [0, 10000]$):
    $$\text{Score} = \frac{\text{verifiedQueries}}{\text{totalQueries}} \times 10.000$$

#### 5.1.4. Chuẩn ERC-8004 Draft Specification
- Chuẩn giao diện cho hệ thống Quản lý Danh tính và Đánh giá Tác tử:
  ```solidity
  interface IERC8004 {
      event AgentRegistered(uint256 indexed agentId, address indexed owner, string domain);
      event ReputationUpdated(uint256 indexed agentId, uint256 newScore, uint256 totalQueries);
      event AgentPolicyUpdated(uint256 indexed agentId, bytes32 newPolicyHash);

      function registerAgent(string calldata domain, string calldata metadataURI, bytes32 capabilityHash, bytes32 policyHash) external returns (uint256 agentId);
      function recordEvaluation(uint256 agentId, bool isVerified, bytes32 proofReceiptHash) external;
      function getAgent(uint256 agentId) external view returns (AgentProfile memory);
      function getReputationScore(uint256 agentId) external view returns (uint256 score);
  }
  ```

#### 5.1.5. Bộ công cụ phát triển Foundry (Forge, Anvil, Cast)
- **Forge**: Bộ công cụ biên dịch và kiểm thử nhanh nhất hiện nay, viết test trực tiếp bằng Solidity (không cần cấu hình JS/TS rườm rà), hỗ trợ Fuzzing testing tự sinh hàng ngàn ca thử nghiệm ngẫu nhiên, Invariant testing kiểm định tính bất biến.
- **Anvil**: Node EVM cục bộ tốc độ cực cao, khởi động tức thì, hỗ trợ fork trạng thái từ mainnet/testnet.
- **Cast**: Công cụ CLI tương tác RPC, chuyển đổi dữ liệu Hex/ABI và gửi giao dịch trực tiếp từ terminal.

#### 5.1.6. Best Practices Bảo mật Smart Contract
- **Chống lỗi Reentrancy**: Sử dụng mẫu kiểm tra trước - thay đổi trạng thái - rồi mới tương tác ngoài (Checks-Effects-Interactions - CEI pattern) kết hợp `ReentrancyGuard` của OpenZeppelin.
- **Kiểm soát phân quyền (Access Control)**: Dùng `Ownable2Step` (ngăn chuyển nhầm quyền sở hữu cho địa chỉ chết) hoặc `AccessControl` phân quyền theo vai trò (RBAC: `ADMIN_ROLE`, `VERIFIER_ROLE`, `LOGGER_ROLE`).
- **Tối ưu hóa Gas qua Opcodes mới (EIP-1153)**: Ứng dụng Transient Storage (`TSTORE`/`TLOAD`) trên Solidity 0.8.24+ để làm Reentrancy Lock tiết kiệm hàng ngàn gas mỗi lượt gọi.

#### 5.1.7. Bảng Đối chiếu Danh pháp Smart Contract giữa ROADMAP và LEARNING_GUIDE
Để bảo đảm tính nhất quán tuyệt đối giữa Kiến trúc Lộ trình triển khai (`docs/ROADMAP.md`) và Giáo trình đào tạo kỹ sư (`docs/LEARNING_GUIDE.md`), bảng đối chiếu dưới đây chuẩn hóa các tên gọi hợp đồng thông minh (Smart Contract Aliases) được sử dụng tương đương trong toàn bộ dự án:

| STT | Tên Hợp đồng trong ROADMAP | Tên Hợp đồng trong LEARNING_GUIDE | Chuẩn Tham chiếu | Phân hệ (Module & Phase) | Chức năng Kỹ thuật Chính |
|:---:|---|---|---|---|---|
| 1 | `TrustAgentRegistry.sol` | `AgentRegistry.sol` | ERC-8004 (Identity Registry) | Module 4 (Phase 3: WBS-3.4) | Đăng ký định danh on-chain cho Agent, quản lý `capabilityHash` và `policyHash`. |
| 2 | `AgentReputationLedger.sol` | `AgentReputation.sol` | ERC-8004 (Reputation Registry) | Module 4 (Phase 3: WBS-3.4) | Lưu trữ bất biến điểm số uy tín, số lượt tư vấn thành công và số lần bị khiếu nại. |
| 3 | `LegalProofAnchor.sol` | `ProvenanceRegistry.sol` | RFC 6962 / Append-Only Merkle Log | Module 5 (Phase 3: WBS-3.7) | Neo Merkle Root của các lô biên lai tư vấn lên Base L2 phục vụ truy vết mật mã. |
| 4 | `LegalCommunityBounty.sol` | `BountyEscrow.sol` | Escrow / Staking & Slashing Model | Module 6 (Phase 4: WBS-4.1) | Quản lý quỹ ký quỹ USDC, nhận 15-20% phí x402, phạt cắt vốn (slash) và giải ngân thưởng. |

*Ghi chú kỹ thuật*: Cả hai quy ước đặt tên đều trỏ đến cùng một logic hợp đồng thông minh. Kỹ sư có thể kế thừa và tạo alias trực tiếp trong mã nguồn Solidity (`contract AgentRegistry is TrustAgentRegistry`) để bảo đảm khả năng tương thích 100% giữa các tài liệu.

---

### 5.2. Kỹ năng thực hành (Practical Skills)

1. Khởi tạo dự án Foundry, quản lý thư viện phụ thuộc bằng `git submodule` (`openzeppelin-contracts`, `forge-std`).
2. Viết Hợp đồng thông minh `AgentRegistry.sol` và `AgentReputation.sol` tuân thủ ERC-8004 bằng Solidity 0.8.24+.
3. Viết bộ kiểm thử toàn diện bằng Foundry (Unit tests, Fuzz tests, Invariant tests) đạt độ bao phủ (Coverage) $> 95\%$.
4. Viết script triển khai (`Deploy.s.sol`) tự động deploy và verify hợp đồng lên mạng Base Sepolia bằng `forge script`.

---

### 5.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)

1. **Decentralized Society: Finding Web3's Soul**  
   - *Tác giả*: E. Glen Weyl, Puja Ohlhaver, Vitalik Buterin.  
   - *Năm*: 2022.  
   - *Giá trị cốt lõi*: Khái niệm về Soulbound Tokens (SBT), danh tính phi tập trung và hệ thống tín nhiệm on-chain.

2. **Smart Contract Security: A Systematic Literature Review**  
   - *Tác giả*: P. Vogel et al.  
   - *Tạp chí*: ACM Computing Surveys (2023).  
   - *Giá trị cốt lõi*: Tổng hợp toàn diện các mẫu lỗ hổng bảo mật smart contract (reentrancy, integer overflow, front-running) và biện pháp phòng chống.

3. **Sách: The Foundry Book**  
   - *Tổ chức*: Paradigm (2024).  
   - *Tài liệu*: [book.getfoundry.sh](https://book.getfoundry.sh).  
   - *Giá trị cốt lõi*: Cẩm nang toàn thư về làm chủ bộ công cụ Foundry.

---

### 5.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)

- **ERC-8004 Draft Standard**: Autonomous Agent Registry & On-chain Reputation Specification.
- **ERC-4337: Account Abstraction Using Alt Mempool**: [eips.ethereum.org/EIPS/eip-4337](https://eips.ethereum.org/EIPS/eip-4337).
- **OpenZeppelin Contracts v5.x Specifications**: Tiêu chuẩn bảo mật thư viện smart contract công nghiệp.

---

### 5.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)

- [foundry-rs/foundry](https://github.com/foundry-rs/foundry): Kho mã nguồn mở chính thức của bộ công cụ Foundry (Forge, Anvil, Cast, Chisel).
- [OpenZeppelin/openzeppelin-contracts](https://github.com/OpenZeppelin/openzeppelin-contracts): Thư viện hợp đồng thông minh chuẩn mực cho Solidity.
- [ethereum-attestation-service/eas-contracts](https://github.com/ethereum-attestation-service/eas-contracts): Hợp đồng thông minh dịch vụ chứng thực Ethereum (EAS), tham chiếu xuất sắc cho hệ thống ghi nhận uy tín on-chain.

---

## 6. MODULE 5: CƠ CHẾ MÃ HÓA BẰNG CHỨNG XUẤT XỨ (CRYPTOGRAPHIC PROVENANCE) & ON-CHAIN MERKLE BATCHING

### 6.1. Kiến thức cốt lõi (Core Concepts)

#### 6.1.1. Hàm băm Mật mã và Dấu vân tay Bằng chứng (Citation Fingerprint)
- **SHA-256 (FIPS 180-4) vs Keccak-256 (FIPS 202)**:
  - SHA-256: Tiêu chuẩn quốc tế ngoài chuỗi (off-chain) để băm dữ liệu lớn, văn bản luật và biên lai.
  - Keccak-256: Tiêu chuẩn gốc của máy ảo EVM, tối ưu hóa gas khi xử lý trên Smart Contract.
- **Citation Fingerprint**: Tạo định danh bất biến cho từng điều khoản luật được tham chiếu:
  $$\text{Fingerprint} = \text{sha256}(\text{document\_id} + \text{"|"} + \text{article\_id} + \text{"|"} + \text{effective\_date} + \text{"|"} + \text{canonical\_text})$$
  Điều này đảm bảo rằng câu trả lời được neo chính xác vào phiên bản luật có hiệu lực tại thời điểm tư vấn, ngăn ngừa gian lận sửa đổi văn bản sau này.

#### 6.1.2. Cấu trúc Cây Merkle và Bằng chứng Thành viên (Merkle Proofs)
- **Cây Merkle (Merkle Tree)**: Cấu trúc cây nhị phân trong đó mỗi nút lá là băm của một bản ghi dữ liệu, và mỗi nút không phải lá là băm của hai nút con:
  $$\text{Node}_{parent} = \text{keccak256}(\text{Node}_{left} \parallel \text{Node}_{right})$$
- **Merkle Proof**: Một danh sách các băm anh chị em (sibling hashes) cho phép chứng minh một phần tử dữ liệu cụ thể nằm trong cây mà chỉ cần $\log_2(N)$ phép tính băm, không cần tiết lộ toàn bộ cây.
- Xác thực trên Solidity thông qua thư viện OpenZeppelin `MerkleProof.sol`:
  ```solidity
  function verify(bytes32[] memory proof, bytes32 root, bytes32 leaf) internal pure returns (bool)
  ```

#### 6.1.3. Cấu trúc Merkle Mountain Range (MMR) cho Dữ liệu Tuần tự
- Cây Merkle truyền thống yêu cầu biết trước toàn bộ số lượng lá và phải cân bằng lại toàn bộ cây khi thêm phần tử mới.
- **Merkle Mountain Range (MMR)**: Cấu trúc tích lũy mật mã chỉ ghi thêm (Append-only Cryptographic Accumulator) gồm danh sách các đỉnh núi (Peaks).
- Phù hợp hoàn hảo cho hệ thống lưu vết dòng xuất xứ (Provenance Stream) của Trust-AGENT: Cho phép ghi nhận biên lai tư vấn pháp lý liên tục theo thời gian thực với chi phí băm cực thấp mà vẫn chứng minh được tính toàn vẹn của lịch sử trong quá khứ.

#### 6.1.4. Quy trình Gom lô Rollup (Batching Rollup Pattern)
- Nếu mỗi câu hỏi pháp lý đều ghi 1 giao dịch lên blockchain: Phí gas tích lũy sẽ làm phá sản dự án và làm nghẽn mạng.
- **Cơ chế Batching Off-chain**:
  1. Thu thập $N$ biên lai (Receipts, ví dụ: $N = 500$ câu hỏi hoặc định kỳ 15 phút một lần).
  2. Mỗi biên lai bao gồm:
     $$\text{Receipt}_i = \text{keccak256}(\text{queryCommitment}_i \parallel \text{evidenceHash}_i \parallel \text{responseHash}_i \parallel \text{timestamp}_i)$$
  3. Dựng Cây Merkle từ $N$ biên lai này để tính ra $\text{MerkleRoot}_{batch}$.
  4. Gửi một giao dịch duy nhất lên hợp đồng `ProvenanceRegistry.sol` trên Base L2 để lưu trữ $\text{MerkleRoot}_{batch}$.
  5. Chi phí gas cho mỗi câu hỏi được giảm đi $N$ lần (chỉ còn vài chục đến vài trăm đơn vị gas).

```
  [Query 1]   [Query 2]   [Query 3]   [Query 4] ... [Query 500]
      │           │           │           │              │
      ▼           ▼           ▼           ▼              ▼
  [Receipt 1] [Receipt 2] [Receipt 3] [Receipt 4] ... [Receipt 500]
      │           │           │           │              │
      └───┬───────┘           └───┬───────┘              │
          ▼                       ▼                      │
       [Node A]                [Node B]                  │
          └───────────┬───────────┘                      │
                      ▼                                  │
                 [Sub-Root 1]                            │
                      └─────────────────┬────────────────┘
                                        ▼
                                [MERKLE ROOT BATCH]
                                        │
                                        ▼ (1 Giao dịch On-chain duy nhất)
                        [ProvenanceRegistry.sol trên Base L2]
```

#### 6.1.5. Kỹ thuật Cam kết có Muối (Salted Commitment) Bảo vệ Quyền riêng tư
- **Vấn đề**: Blockchain là công khai minh bạch. Nếu ghi trực tiếp nội dung câu hỏi hoặc băm thuần túy của câu hỏi lên chuỗi, kẻ xấu có thể dùng từ điển (Rainbow table attack) để suy luận câu hỏi pháp lý nhạy cảm của người dùng (vi phạm Nghị định 13/2023/NĐ-CP về Bảo vệ dữ liệu cá nhân).
- **Giải pháp Salted Commitment**:
  $$\text{Salt} \xleftarrow{\text{random}} \{0, 1\}^{256}$$
  $$\text{QueryCommitment} = \text{HMAC-SHA256}(\text{Key}=\text{Salt}, \text{Message}=\text{CleanQuery})$$
- Người dùng nhận được `Salt` trong biên lai trả về và lưu giữ bí mật.
- Khi xảy ra tranh chấp pháp lý hoặc khiếu nại chất lượng, người dùng mới công bố `Salt` và nội dung câu hỏi để bất kỳ ai cũng có thể tái tạo `QueryCommitment`, xác minh Merkle Proof đối chiếu với Merkle Root đã neo trên blockchain.

#### 6.1.6. Bảng Đối chiếu Danh pháp Smart Contract Lưu vết và Bằng chứng
Nhằm thống nhất danh pháp giữa tài liệu Lộ trình (`docs/ROADMAP.md`) và Giáo trình học tập (`docs/LEARNING_GUIDE.md`), các hợp đồng thông minh cốt lõi liên quan đến lưu vết bằng chứng xuất xứ và phân hệ Web3 được ánh xạ chuẩn hóa như sau:

| STT | Tên Hợp đồng trong ROADMAP | Tên Hợp đồng trong LEARNING_GUIDE | Chuẩn Tham chiếu | Phân hệ (Module & Phase) | Chức năng Kỹ thuật Chính |
|:---:|---|---|---|---|---|
| 1 | `LegalProofAnchor.sol` | `ProvenanceRegistry.sol` | RFC 6962 / Append-Only Merkle Log | Module 5 (Phase 3: WBS-3.7) | Neo Merkle Root của các lô biên lai tư vấn lên Base L2 phục vụ truy vết mật mã. |
| 2 | `TrustAgentRegistry.sol` | `AgentRegistry.sol` | ERC-8004 (Identity Registry) | Module 4 (Phase 3: WBS-3.4) | Đăng ký định danh on-chain cho Agent, quản lý `capabilityHash` và `policyHash`. |
| 3 | `AgentReputationLedger.sol` | `AgentReputation.sol` | ERC-8004 (Reputation Registry) | Module 4 (Phase 3: WBS-3.4) | Lưu trữ bất biến điểm số uy tín, số lượt tư vấn thành công và số lần bị khiếu nại. |
| 4 | `LegalCommunityBounty.sol` | `BountyEscrow.sol` | Escrow / Staking & Slashing Model | Module 6 (Phase 4: WBS-4.1) | Quản lý quỹ ký quỹ USDC, nhận 15-20% phí x402, phạt cắt vốn (slash) và giải ngân thưởng. |

*Ghi chú kỹ thuật*: Trong các ví dụ thực hành của Module 5, hợp đồng `ProvenanceRegistry.sol` đóng vai trò chính là `LegalProofAnchor.sol` (WBS-3.7) thực hiện nhiệm vụ chốt chặn dữ liệu Merkle Root lên chuỗi.

---

### 6.2. Kỹ năng thực hành (Practical Skills)

1. Lập trình module Python tạo Merkle Tree chuẩn hóa (sắp xếp cặp nút con lexicographically để đảm bảo tính xác định).
2. Lập trình Hợp đồng `ProvenanceRegistry.sol` lưu trữ lịch sử các Merkle Roots kèm hàm `verifyProof`.
3. Xây dựng Batching Daemon chạy ngầm thu gom biên lai từ cơ sở dữ liệu, dựng Merkle Tree và tự động gửi giao dịch gom lô lên mạng Base Sepolia.
4. Triển khai thuật toán Salted Commitment và sinh tệp chứng chỉ chứng minh nguồn gốc định dạng JSON (`provenance_receipt.json`) bàn giao cho người dùng.

---

### 6.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)

1. **A Certified Digital Signature**  
   - *Tác giả*: Ralph C. Merkle.  
   - *Hội nghị*: CRYPTO 1979 (Xuất bản: Communications of the ACM).  
   - *Giá trị cốt lõi*: Công trình toán học nền tảng phát minh ra cấu trúc Merkle Tree.

2. **Merkle Mountain Ranges (MMR)**  
   - *Tác giả*: Peter Todd.  
   - *Năm*: 2012.  
   - *Tài liệu*: [github.com/opentimestamps/opentimestamps-server](https://github.com/opentimestamps/opentimestamps-server).  
   - *Giá trị cốt lõi*: Đặc tả cấu trúc cây tích lũy log nối tiếp cho các hệ thống timestamping phân tán.

3. **Sách: Introduction to Modern Cryptography**  
   - *Tác giả*: Jonathan Katz, Yehuda Lindell.  
   - *Nhà xuất bản*: CRC Press (3rd Edition, 2020).  
   - *Giá trị cốt lõi*: Giáo trình chuẩn mực quốc tế về hàm băm mật mã, tính kháng va chạm và lược đồ cam kết (Commitment schemes).

---

### 6.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)

- **RFC 6962: Certificate Transparency (Append-Only Merkle Tree Logs & Audit Proofs)**: Tiêu chuẩn IETF chuẩn mực quốc tế quy định định dạng cây Merkle bất biến chỉ ghi thêm, cơ chế băm phân tách miền tiền tố (`0x00` cho lá, `0x01` cho nút cha), và các thuật toán toán học kiểm toán bằng chứng thành viên (Inclusion Proofs / Audit Paths) và tính nhất quán (Consistency Proofs).
- **NIST FIPS 180-4: Secure Hash Standard (SHS - SHA-256)**.
- **NIST FIPS 202: SHA-3 Standard: Permutation-Based Hash and Extendable-Output Functions (Keccak-256)**.
- **OpenZeppelin Contracts MerkleProof Library Specification**.
- **Nghị định số 13/2023/NĐ-CP của Chính phủ Việt Nam về Bảo vệ dữ liệu cá nhân**.

---

### 6.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)

- [OpenZeppelin/merkle-tree](https://github.com/OpenZeppelin/merkle-tree): Thư viện JavaScript/TypeScript chuẩn để sinh cây và bằng chứng Merkle tương thích 100% với Solidity.
- [mimblewimble/grin](https://github.com/mimblewimble/grin): Triển khai tham chiếu của Merkle Mountain Range (MMR) hiệu năng cao bằng Rust.
- [pyca/cryptography](https://github.com/pyca/cryptography): Thư viện mật mã chuẩn mực cho Python hỗ trợ HMAC, SHA-256 và các nguyên thủy an toàn.

---

## 7. MODULE 6: CƠ CHẾ KINH TẾ TOKEN & HỆ THỐNG TRẢ THƯỞNG CỘNG ĐỒNG (WEB3 BOUNTY SYSTEM)

### 7.1. Kiến thức cốt lõi (Core Concepts)

#### 7.1.1. Lý thuyết Trò chơi (Game Theory) và Thiết kế Cơ chế (Mechanism Design)
- **Điểm Schelling (Schelling Point / Focal Point)**: Khái niệm trong lý thuyết trò chơi phi hợp tác (Non-cooperative game theory) chỉ ra giải pháp mà các bên độc lập sẽ tự nhiên hội tụ về khi không thể giao tiếp với nhau.
  - Áp dụng vào thẩm định luật: Nếu một câu trả lời trích dẫn sai luật, một hội đồng giám khảo độc lập khi được hỏi sẽ cùng chỉ ra điểm sai đó vì "Sự thật khách quan trong văn bản luật" là điểm Schelling duy nhất.
- **Khả năng tương thích động cơ (Incentive Compatibility)**: Thiết kế hệ thống sao cho hành động trung thực (đóng góp văn bản luật chuẩn, báo lỗi chính xác) đem lại lợi nhuận kỳ vọng cao nhất cho người tham gia.
- **Kháng tấn công mạo danh (Sybil Resistance)**: Bắt buộc người gửi báo cáo hoặc tham gia thẩm định phải ký quỹ tài sản (Staking), triệt tiêu động cơ tạo hàng loạt tài khoản giả để thao túng.

#### 7.1.2. Hợp đồng Thông minh Ký quỹ & Bể thưởng (Bounty Escrow & Pool)
- Quản trị vòng đời quỹ thưởng cộng đồng:
  1. **Nạp quỹ (Fund)**: Dự án hoặc nhà tài trợ nạp USDC / Token quản trị vào `BountyEscrow.sol`.
  2. **Tạo thách thức (Create Bounty Issue)**: Treo thưởng cho việc bổ sung văn bản luật mới (ví dụ: bóc tách Nghị định 168/2024/NĐ-CP) hoặc treo thưởng tìm kiếm ảo giác trong câu trả lời đã lưu vết on-chain.
  3. **Đệ trình (Submit & Stake)**: Thợ săn tiền thưởng (Bounty Hunter) nộp bài kèm khoản cọc bắt buộc (`submissionStake`).
  4. **Giải ngân (Payout)**: Khi báo cáo được thẩm định hợp lệ, hợp đồng tự động chuyển tiền thưởng kèm hoàn trả cọc.

#### 7.1.3. Cơ chế Đặt cọc (Staking) & Phạt cắt vốn (Slashing) Chống Spam
- **Quy tắc trừng phạt**:
  $$\text{Payout} = \begin{cases} 
  \text{BountyReward} + \text{Stake}, & \text{nếu Báo cáo Đúng (Valid)} \\
  0, & \text{nếu Báo cáo Bị bác bỏ vô căn cứ (Spam)} \implies \text{Bị phạt Slashing } 100\% \text{ cọc} \\
  \text{Stake}, & \text{nếu Tranh chấp bất phân thắng bại (Draw)}
  \end{cases}$$
- Lượng tiền cọc bị phạt (Slashed funds) được chia làm 2 phần: 50% chuyển vào Bể thưởng chung (Bounty Pool), 50% thưởng cho người/hội đồng giám khảo đã phát hiện hành vi spam.

#### 7.1.4. Mô hình Phân xử Tranh chấp Phi tập trung (Kleros Dispute Model)
- Khi có sự bất đồng giữa Agent và Người dùng về tính chính xác của câu trả lời pháp lý:
  - Vụ việc được chuyển đến Tòa án phi tập trung (Decentralized Arbitration Court).
  - Một nhóm Giám khảo (Jurors) được bốc thăm ngẫu nhiên có trọng số dựa trên lượng token đã stake.
  - **Bỏ phiếu Kín Cam kết - Tiết lộ (Commit-Reveal Voting)**:
    - *Giai đoạn Cam kết*: Giám khảo gửi băm kín $\text{keccak256}(\text{Vote} \parallel \text{SecretSalt})$ để không ai biết người khác bỏ phiếu thế nào.
    - *Giai đoạn Tiết lộ*: Mở vote công khai.
  - Giám khảo nào bỏ phiếu theo phe đa số (Schelling Point) sẽ được chia tiền thưởng phân xử; giám khảo bỏ phiếu cho phe thiểu số (sai lệch sự thật) sẽ bị tịch thu token cọc chia cho phe thắng.

---

### 7.2. Kỹ năng thực hành (Practical Skills)

1. Thiết kế và lập trình Smart Contract `BountyEscrow.sol` bằng Solidity 0.8.24+ quản lý ký quỹ an toàn tuyệt đối.
2. Cài đặt cơ chế Staking và Slashing có điều kiện với quyền phân xử rõ ràng.
3. Lập trình lược đồ Commit-Reveal Voting trên hợp đồng thông minh để chống gian lận nhìn trước kết quả.
4. Xây dựng giao diện Web hoặc API cho phép cộng đồng nộp văn bản luật mới và theo dõi trạng thái thẩm duyệt.

---

### 7.3. Giáo trình, Nghiên cứu & Sách kinh điển (Research Papers & Books)

1. **Kleros: Short Paper v1.0.7**  
   - *Tác giả*: Clément Lesaege, Federico Ast.  
   - *Năm*: 2018.  
   - *Tài liệu*: [kleros.io/whitepaper.pdf](https://kleros.io/whitepaper.pdf).  
   - *Giá trị cốt lõi*: Lý thuyết kinh tế học mật mã xây dựng hệ thống tòa án phân xử phi tập trung dựa trên Schelling Point.

2. **The Strategy of Conflict**  
   - *Tác giả*: Thomas C. Schelling (Chủ nhân giải Nobel Kinh tế).  
   - *Nhà xuất bản*: Harvard University Press (1960).  
   - *Giá trị cốt lõi*: Tác phẩm kinh điển khai sinh khái niệm Focal Point (Điểm Schelling) trong lý thuyết trò chơi.

3. **Twenty Lectures on Algorithmic Game Theory**  
   - *Tác giả*: Tim Roughgarden (Stanford University / Columbia University).  
   - *Nhà xuất bản*: Cambridge University Press (2016).  
   - *Giá trị cốt lõi*: Giáo trình giải thuật thiết kế cơ chế, đấu giá và động cơ kinh tế trong khoa học máy tính.

---

### 7.4. Tiêu chuẩn và Đặc tả kỹ thuật (Official Standards & Specs)

- **ERC-20: Fungible Token Standard**: Chuẩn token thanh toán và quản trị.
- **ERC-792: Arbitration Standard**: Chuẩn giao tiếp giữa hợp đồng phát sinh tranh chấp (Arbitrable) và hợp đồng tòa án phân xử (Arbitrator).
- **ERC-1497: Evidence Standard for Arbitrable Contracts**: Chuẩn cấu trúc dữ liệu lưu trữ bằng chứng phục vụ phân xử pháp lý phi tập trung.

---

### 7.5. Dự án mã nguồn mở tham khảo (Open-Source Reference Repositories)

- [kleros/kleros-v2](https://github.com/kleros/kleros-v2): Nền tảng phân xử tranh chấp phi tập trung hàng đầu Web3 triển khai ERC-792.
- [gitcoinco/grants-stack](https://github.com/gitcoinco/grants-stack): Khung phân bổ quỹ cộng đồng và cơ chế tài trợ bậc hai (Quadratic Funding).
- [aragon/osx](https://github.com/aragon/osx): Kiến trúc quản trị DAO mô-đun hóa và hệ thống bỏ phiếu phi tập trung an toàn.

---

## 8. LỘ TRÌNH HỌC TẬP CÓ CẤU TRÚC 12 TUẦN (12-WEEK STRUCTURED ROADMAP)

> **💡 CHÚ THÍCH ĐỒNG HÀNH VỀ KHUNG THỜI GIAN (12 TUẦN ĐÀO TẠO $\leftrightarrow$ 24 TUẦN DỰ ÁN)**:  
> - **Lộ trình 12 tuần trong LEARNING_GUIDE**: Là khung thời gian tự học và đào tạo năng lực cá nhân tập trung (Fast-track Personal Boot-up) của kỹ sư AI/Web3 để làm chủ toàn bộ nền tảng lý thuyết và công nghệ chuyên sâu qua 4 chặng học tập.  
> - **Lộ trình 24 tuần (12 Sprints $\times$ 2 tuần/Sprint) trong ROADMAP.md**: Là khung thời gian triển khai dự án công nghiệp thực tế ở quy mô tổ chức (với 4 Squads chuyên môn), bao gồm các chu trình thu thập làm sạch dữ liệu lớn, kiểm thử hồi quy, audit bảo mật smart contract, vận hành thử nghiệm phân xử DAO và tích hợp End-to-End toàn diện.  
> - **Tính tương thích và đồng hành**: Khung thời gian đào tạo 12 tuần hoàn toàn tương thích và đồng hành nhịp nhàng với dự án 24 tuần. Kỹ sư hoàn thành Chặng 1 (Tuần 1-3) sẽ tham gia ngay vào Sprint 1-4 (Phase 1 & 2); hoàn thành Chặng 2 (Tuần 4-6) đáp ứng các nhiệm vụ kiểm định RAG của Sprint 5-6; hoàn thành Chặng 3 & 4 (Tuần 7-12) làm chủ toàn bộ hạ tầng Web3, Smart Contract Foundry, x402 và Provenance Merkle Root của Phase 3 & 4 (Sprint 7-12).

Lộ trình được thiết kế theo 4 chặng logic, giúp kỹ sư đi từ kiến trúc cốt lõi đến khi làm chủ toàn diện hệ thống production sẵn sàng audit.

```
       CHẶNG 1: NỀN TẢNG                 CHẶNG 2: ADVANCED RAG             CHẶNG 3: WEB3 FULLSTACK           CHẶNG 4: PROVENANCE & PROD
       (Tuần 1 - 3)                      (Tuần 4 - 6)                      (Tuần 7 - 9)                      (Tuần 10 - 12)
┌───────────────────────────────┐ ┌───────────────────────────────┐ ┌───────────────────────────────┐ ┌───────────────────────────────┐
│ • LangGraph StateGraph        │ │ • Hybrid (BM25 + Dense)       │ │ • Solidity 0.8.24+ & Foundry  │ │ • Merkle Proof & MMR Rollup   │
│ • ReAct Loop & Memory Saver   │ │ • RRF Fusion (k=60)           │ │ • EIP-712 & EIP-3009 Gasless  │ │ • Salted Privacy Commitments  │
│ • VN Legal Hierarchy Parser   │ │ • BGE-Reranker v2 M3          │ │ • x402 Micropayment Server    │ │ • Bounty Escrow & Slashing    │
│ • Semantic Query Decomp DAG   │ │ • NLI Entailment Guardrails   │ │ • ERC-8004 Agent Registry L2  │ │ • Security Audit & Hardening  │
└───────────────────────────────┘ └───────────────────────────────┘ └───────────────────────────────┘ └───────────────────────────────┘
```

---

### 8.1. Chặng 1 (Tuần 1 - 3): Nền tảng Multi-Agent & Kỹ thuật Dữ liệu Pháp luật Việt Nam

#### Tuần 1: Làm chủ LangGraph và Chu trình Tác tử ReAct
- **Mục tiêu**: Nắm vững cơ chế StateGraph, Reducers, và luồng suy luận hành động ReAct.
- **Nội dung lý thuyết**:
  - Kiến trúc LangGraph v0.2: Nút, cạnh có điều kiện, quản lý trạng thái luồng.
  - Nguyên lý ReAct: Phân biệt Thought, Action, Action Input, Observation.
  - Phân tích mã nguồn hiện tại `crawl/app/router.py` và `crawl/app/agents/base.py`.
- **Thực hành**:
  - Dựng một ReAct Agent độc lập với công cụ tính toán ngày có hiệu lực của văn bản luật.
  - Viết Unit test kiểm tra dừng vòng lặp an toàn khi gặp lỗi công cụ.

#### Tuần 2: Cấu trúc Thể chế Pháp luật Việt Nam & Bộ Bóc tách Phân cấp (Hierarchical Parser)
- **Mục tiêu**: Bóc tách chuẩn xác văn bản pháp luật mà không làm xé nát ngữ cảnh.
- **Nội dung lý thuyết**:
  - Nghiên cứu Luật Ban hành VBQPPL và Nghị định 34/2016/NĐ-CP (quy chuẩn thể thức).
  - Phân tích sự cố dữ liệu Thuế (`crawl/data/raw/thue.json` thực chất là Luật Kế toán).
  - Kỹ thuật xây dựng Legal AST (Abstract Syntax Tree) cho cấu trúc Chương/Điều/Khoản/Điểm.
- **Thực hành**:
  - Viết Parser bóc tách toàn văn Bộ luật Lao động 2019 và Luật Quản lý Thuế 2019 thành các chunks JSON có gắn Breadcrumb header đầy đủ.
  - Loại bỏ hoàn toàn 2 bản ghi trùng lặp trong dữ liệu Lao động hiện có.

#### Tuần 3: Xây dựng Master Router Đa tầng & Bộ nhớ Trạng thái Bền vững (Stateful Memory)
- **Mục tiêu**: Nâng cấp Router hiện tại từ Stateless sang Stateful đa phiên và phân tách truy vấn DAG.
- **Nội dung lý thuyết**:
  - Kỹ thuật lưu vết trạng thái với `PostgresSaver` / `RedisSaver`.
  - Phân rã câu hỏi đa miền phức tạp (Semantic Query Decomposition).
  - Tổng hợp câu trả lời đa ngành có suy luận pháp lý thay vì nối chuỗi văn bản thô `\n\n`.
- **Thực hành**:
  - Cấu hình PostgreSQL local và tích hợp `PostgresSaver` vào `RouterState`.
  - Viết node Synthesizer sử dụng LLM để đối chiếu và kết luận khi nhận kết quả từ 2 domain khác nhau.
- **Nghiệm thu Chặng 1**: Hoàn thành [Capstone Project 1](#91-capstone-1-multi-agent-legal-dispatcher-với-langgraph--bộ-bóc-tách-luật-phân-cấp).

---

### 8.2. Chặng 2 (Tuần 4 - 6): Advanced Legal RAG, Hybrid Retrieval & Thẩm định Ảo giác

#### Tuần 4: Động cơ Tìm kiếm Lai (Hybrid Search: Dense Vector + Sparse BM25Okapi)
- **Mục tiêu**: Khắc phục nhược điểm mất thuật ngữ chính xác của Vector search thuần túy.
- **Nội dung lý thuyết**:
  - Cơ chế hoạt động của BM25Okapi và sự cần thiết của Vietnamese Word Segmentation.
  - Mô hình Embedding đa ngôn ngữ `BAAI/bge-m3` và quản lý ChromaDB collections.
- **Thực hành**:
  - Tích hợp `underthesea` vào module `retrieval.py` để bẻ từ câu hỏi và tài liệu trước khi nạp vào BM25.
  - Chạy thực nghiệm so sánh độ phủ tìm kiếm giữa BM25 thường và BM25 đã qua bẻ từ tiếng Việt.

#### Tuần 5: Hợp nhất RRF ($k=60$) & Tối ưu hóa Cross-Encoder Reranking
- **Mục tiêu**: Nâng cao độ chính xác Top-5 tài liệu đưa vào Prompt lên trên 90%.
- **Nội dung lý thuyết**:
  - Giải thuật Reciprocal Rank Fusion (RRF) với hằng số $k=60$.
  - Sự khác biệt về kiến trúc giữa Bi-Encoder và Cross-Encoder.
  - Mô hình `BAAI/bge-reranker-v2-m3`.
- **Thực hành**:
  - Viết module `reranker.py` tải mô hình Cross-Encoder, chấm điểm lại Top-30 tài liệu từ RRF.
  - Đo lường độ trễ (Latency benchmark) và cấu hình batch size tối ưu.

#### Tuần 6: Xây dựng Cross-checking Agent: NLI Entailment Guardrails & Lọc Hiệu lực Thời gian
- **Mục tiêu**: Loại trừ 100% ảo giác trích dẫn sai luật và cảnh báo văn bản hết hiệu lực.
- **Nội dung lý thuyết**:
  - Lược đồ Natural Language Inference (Premise vs Hypothesis).
  - Thuật toán đối chiếu trường `effective_from` và `expiry_date` với thời điểm phát sinh sự vụ.
- **Thực hành**:
  - Viết `CrossCheckingAgent` kiểm tra từng câu khẳng định trong câu trả lời đối chiếu với điều luật trích dẫn.
  - Tạo bộ test 20 câu hỏi bẫy luật hết hiệu lực (ví dụ: bẫy Nghị định 100/2019/NĐ-CP về giao thông đã bị sửa đổi).
- **Nghiệm thu Chặng 2**: Hoàn thành [Capstone Project 2](#92-capstone-2-động-cơ-hybrid-legal-rag-đa-miền-với-bge-reranker--nli-guardrail).

---

### 8.3. Chặng 3 (Tuần 7 - 9): Web3 Fullstack, Smart Contract Foundry, x402 & ERC-8004

#### Tuần 7: Lập trình Smart Contract Chuyên sâu với Foundry
- **Mục tiêu**: Làm chủ bộ công cụ Foundry (Forge, Anvil, Cast) và ngôn ngữ Solidity 0.8.24+.
- **Nội dung lý thuyết**:
  - Cấu trúc dự án Foundry, quản lý thư viện phụ thuộc OpenZeppelin.
  - EVM Storage Layout, Transient Storage (EIP-1153), Custom Errors, Gas Optimization.
  - Kỹ thuật viết test bằng Solidity thuần: Fuzz testing và Invariant testing.
- **Thực hành**:
  - Cài đặt Foundry và viết smart contract lưu trữ dữ liệu đơn giản.
  - Viết Fuzz test kiểm tra trường hợp tràn số và ranh giới tham số.

#### Tuần 8: Ký số EIP-712 & Giao thức Thanh toán Vi mô x402 với EIP-3009 Gasless USDC
- **Mục tiêu**: Xây dựng luồng thanh toán vi mô không tốn gas trên mạng Layer-2 Base.
- **Nội dung lý thuyết**:
  - Cấu trúc Domain Separator và StructHash trong EIP-712.
  - Phương thức `transferWithAuthorization` của chuẩn EIP-3009 trên hợp đồng USDC.
  - Quy trình Challenge - Response của mã trạng thái HTTP 402.
- **Thực hành**:
  - Xây dựng Middleware FastAPI interceptor chặn request và trả về HTTP 402.
  - Viết Client Python ký số EIP-712 và Facilitator Server xác minh chữ ký, gọi rút tiền USDC trên Base Sepolia.

#### Tuần 9: Triển khai Chuẩn ERC-8004: Agent Identity & On-chain Reputation Ledger
- **Mục tiêu**: Khởi tạo định danh on-chain cho các Agent chuyên ngành pháp lý và sổ cái chấm điểm tín nhiệm.
- **Nội dung lý thuyết**:
  - Phân tích dự thảo chuẩn ERC-8004.
  - Cơ chế băm cam kết năng lực `capabilityHash` và `policyHash`.
  - Thuật toán cập nhật điểm uy tín theo tỷ lệ `verifiedQueries / totalQueries`.
- **Thực hành**:
  - Lập trình `AgentRegistry.sol` và `AgentReputation.sol` bằng Foundry.
  - Đăng ký định danh cho 3 Agent (Traffic, Labor, Tax) lên mạng thử nghiệm Base Sepolia.
- **Nghiệm thu Chặng 3**: Hoàn thành [Capstone Project 3](#93-capstone-3-cổng-thanh-toán-vi-mô-x402-eip-3009-usdc--sổ-cái-erc-8004-trên-l2).

---

### 8.4. Chặng 4 (Tuần 10 - 12): Merkle Provenance Rollup, Sàn thưởng Bounty & Production Hardening

#### Tuần 10: Merkle Tree Batching Rollup & Kỹ thuật Salted Privacy Commitment
- **Mục tiêu**: Lưu vết bằng chứng xuất xứ tư vấn pháp lý lên blockchain với chi phí tối thiểu và bảo vệ quyền riêng tư người dùng.
- **Nội dung lý thuyết**:
  - Giải thuật dựng cây Merkle chuẩn hóa và sinh Merkle Proof.
  - Thư viện `MerkleProof.sol` của OpenZeppelin.
  - Thuật toán Salted Commitment với HMAC-SHA256 tuân thủ Nghị định 13/2023/NĐ-CP.
- **Thực hành**:
  - Viết Smart Contract `ProvenanceRegistry.sol` lưu trữ Merkle Root định kỳ.
  - Viết Batcher Daemon tự động gom 100 biên lai tư vấn, dựng Merkle Tree và gửi giao dịch lên Base L2.
  - Viết module sinh file `provenance_receipt.json` kèm Salt cho người dùng.

#### Tuần 11: Thiết kế Cơ chế Game Theory, Smart Contract Escrow Bounty & Phân xử Kleros
- **Mục tiêu**: Xây dựng quỹ thưởng cộng đồng tự vận hành chống gian lận và spam.
- **Nội dung lý thuyết**:
  - Điểm Schelling và động cơ kinh tế trong việc thẩm định dữ liệu.
  - Kiến trúc Ký quỹ (Escrow), Staking và Slashing.
  - Mô hình tòa án phi tập trung (Kleros arbitration) với cơ chế Commit-Reveal voting.
- **Thực hành**:
  - Lập trình `BountyEscrow.sol` cho phép nạp thưởng, nhận bài nộp kèm cọc stake, và tự động xử phạt slash nếu báo cáo là spam.
  - Viết test mô phỏng kịch bản tấn công spam và xác thực cơ chế bảo vệ quỹ thưởng.

#### Tuần 12: Đóng gói Hệ thống Hoàn chỉnh, Kiểm toán Bảo mật (Security Audit) & Production Deployment
- **Mục tiêu**: Tích hợp toàn diện toàn bộ các phân hệ, chạy benchmark hiệu năng và kiểm toán an toàn.
- **Nội dung lý thuyết**:
  - Phương pháp kiểm toán bảo mật Smart Contract: Phân tích tĩnh với Slither, kiểm thử bất biến Echidna.
  - Tối ưu hóa hiệu năng API Gateway và quản lý kết nối cơ sở dữ liệu.
- **Thực hành**:
  - Chạy Slither quét toàn bộ smart contracts và khắc phục mọi cảnh báo mức Medium/High.
  - Đóng gói toàn bộ hệ thống (FastAPI, LangGraph, ChromaDB, Postgres, Batcher Daemon) bằng Docker Compose.
  - Thực hiện kiểm thử tải đầu - cuối (End-to-End Stress Test).
- **Nghiệm thu Chặng 4**: Hoàn thành [Capstone Project 4](#94-capstone-4-nền-tảng-trust-agent-hoàn-chỉnh-merkle-rollup--hệ-thống-escrow-bounty).

---

## 9. DỰ ÁN THỰC HÀNH MẪU (CAPSTONE PROJECTS)

Để củng cố kỹ năng và chứng minh năng lực thực tế, học viên bắt buộc phải hoàn thành 4 dự án Capstone tương ứng với 4 chặng học tập:

---

### 9.1. Capstone 1: Multi-Agent Legal Dispatcher với LangGraph & Bộ bóc tách Luật phân cấp

#### Mục tiêu Dự án
Xây dựng một hệ thống điều phối tác tử pháp lý độc lập có khả năng phân tách câu hỏi đa ngành, ghi nhớ lịch sử hội thoại nhiều lượt qua PostgreSQL và bóc tách dữ liệu luật có cấu trúc Breadcrumb phân cấp.

#### Yêu cầu Kiến trúc & Kỹ thuật
1. **Parser Phân cấp (Hierarchical Parser)**:
   - Viết parser xử lý tệp văn bản luật (HTML/JSON) thành danh mục các chunk Khoản/Điều.
   - Mỗi chunk phải có metadata: `law_id`, `chapter_id`, `article_id`, `clause_id`, `effective_from`, `status`.
2. **LangGraph StateGraph**:
   - Định nghĩa `RouterState` quản lý `thread_id`, danh sách câu hỏi con `sub_queries`, kết quả từng domain, và `final_answer`.
   - Nút `Classifier`: Sử dụng Pydantic Structured Output phân loại chính xác các domain `traffic`, `labor`, `tax`.
   - Nút `Synthesizer`: Kết hợp và đối chiếu logic giữa các domain thay vì nối chuỗi văn bản thô.
3. **Bộ nhớ Trạng thái**:
   - Sử dụng `PostgresSaver` để duy trì ngữ cảnh khi người dùng hỏi các câu tiếp nối (ví dụ: *"Thế còn mức phạt đối với xe máy thì sao?"*).

#### Tiêu chí Nghiệm thu (Acceptance Criteria)
- [ ] Bóc tách thành công 100% các điều khoản của Bộ luật Lao động 2019 và Luật Quản lý Thuế 2019 mà không bị lỗi đứt đoạn ngữ cảnh.
- [ ] Xử lý đúng ít nhất 10 ca câu hỏi đa ngành phức tạp với thời gian phản hồi $< 3.0\text{s}$.
- [ ] Duy trì đúng ngữ cảnh hội thoại qua tối thiểu 5 lượt hỏi đáp liên tiếp với cùng một `thread_id`.

---

### 9.2. Capstone 2: Động cơ Hybrid Legal RAG Đa miền với BGE-Reranker & NLI Guardrail

#### Mục tiêu Dự án
Xây dựng động cơ tìm kiếm và sinh câu trả lời pháp lý chuẩn xác cao, loại bỏ hoàn toàn hiện tượng ảo giác trích dẫn và văn bản hết hiệu lực trên 3 mảng: Giao thông, Lao động, Thuế.

#### Yêu cầu Kiến trúc & Kỹ thuật
1. **Hybrid Retrieval**:
   - Tích hợp `underthesea` bẻ từ tiếng Việt vào BM25Okapi.
   - Tích hợp ChromaDB lưu trữ vector embeddings (`BAAI/bge-m3`).
   - Kết hợp kết quả bằng thuật toán RRF với $k = 60$.
2. **Cross-Encoder Reranking**:
   - Tích hợp mô hình `BAAI/bge-reranker-v2-m3` để chọn lọc Top-5 tài liệu có liên quan nhất từ Top-40 tài liệu thô.
3. **NLI Hallucination Cross-Checker**:
   - Viết module kiểm duyệt NLI đối chiếu từng câu trong câu trả lời với các điều khoản luật được trích dẫn.
   - Nếu phát hiện nhãn `Contradiction` hoặc `Neutral` trên các tuyên bố quan trọng, lập tức kích hoạt cơ chế Fallback hoặc gắn nhãn cảnh báo.
4. **Bộ lọc Hiệu lực Thời gian (Temporal Filter)**:
   - Truy vấn bắt buộc đối chiếu ngày sự vụ với `effective_from` và `expiry_date`.

#### Tiêu chí Nghiệm thu (Acceptance Criteria)
- [ ] Đạt chỉ số Hit Rate@5 $> 92\%$ và MRR@5 $> 0.85$ trên bộ dữ liệu kiểm thử chuẩn 100 câu hỏi pháp lý Việt Nam.
- [ ] Phát hiện và chặn đứng 100% các ca thử nghiệm cố tình đưa thông tin sai lệch hoặc trích dẫn văn bản đã hết hiệu lực.
- [ ] Độ trễ tổng thể của chuỗi RAG (Retrieval + Rerank + LLM + NLI Guardrail) $< 2.5\text{s}$ trên GPU T4/A10G hoặc tương đương.

---

### 9.3. Capstone 3: Cổng thanh toán vi mô x402 (EIP-3009 USDC) & Sổ cái ERC-8004 trên L2

#### Mục tiêu Dự án
Xây dựng phân hệ thương mại hóa API tự động cho tác tử AI: Người dùng trả tiền vi mô bằng USDC thông qua chữ ký EIP-3009 không tốn gas, và hệ thống ghi nhận uy tín của Agent lên Smart Contract ERC-8004 trên mạng Base Sepolia.

#### Yêu cầu Kiến trúc & Kỹ thuật
1. **Middleware HTTP 402**:
   - Triển khai trên FastAPI, chặn mọi request chưa thanh toán, sinh challenge EIP-712 chứa `nonce`, `price`, `deadline`.
2. **Client Signer & Relayer**:
   - Client tự động ký ủy quyền EIP-3009 `transferWithAuthorization`.
   - Facilitator Server xác minh chữ ký và gửi giao dịch lên hợp đồng USDC Base Sepolia.
3. **Smart Contract ERC-8004 (Foundry)**:
   - Viết `AgentRegistry.sol` đăng ký năng lực của Agent kèm `capabilityHash` và `policyHash`.
   - Viết `AgentReputation.sol` ghi nhận điểm uy tín bất biến dựa trên tỷ lệ câu trả lời trích dẫn chính xác.
   - Viết đầy đủ Unit tests và Fuzz tests bằng Forge đạt độ bao phủ $> 95\%$.

#### Tiêu chí Nghiệm thu (Acceptance Criteria)
- [ ] Thực hiện thành công luồng gọi API trả phí từ Client đến Server mà Client không phải trả ETH làm phí gas.
- [ ] Smart Contract vượt qua 100% các bài test trong Foundry mà không phát sinh lỗi bảo mật Reentrancy hay Overflow.
- [ ] Hợp đồng được triển khai và verify thành công trên mạng thử nghiệm Base Sepolia.

---

### 9.4. Capstone 4: Nền tảng Trust-AGENT Hoàn chỉnh: Merkle Rollup & Hệ thống Escrow Bounty

#### Mục tiêu Dự án
Tích hợp toàn diện toàn bộ các module thành sản phẩm hoàn chỉnh cấp sản xuất (Production-grade): Neo bằng chứng xuất xứ Merkle Root lên blockchain, bảo vệ quyền riêng tư qua Salted Commitment, và vận hành bể thưởng cộng đồng Escrow Bounty chống spam.

#### Yêu cầu Kiến trúc & Kỹ thuật
1. **Cryptographic Provenance Engine**:
   - Mỗi câu trả lời sinh ra một biên lai gồm: `SaltedQueryHash`, `EvidenceFingerprint`, `ResponseHash`, `Timestamp`.
   - Batcher Daemon gom biên lai theo lô (100 câu hỏi/lô), dựng Merkle Tree và gửi giao dịch lưu Merkle Root lên `ProvenanceRegistry.sol`.
   - Người dùng có thể dùng `provenance_receipt.json` và công cụ CLI để tự xác minh bằng chứng độc lập trên blockchain.
2. **Hệ thống Escrow & Bounty Pool Chống Spam**:
   - Viết Smart Contract `BountyEscrow.sol` quản lý quỹ thưởng USDC.
   - Thợ săn tiền thưởng nộp phát hiện lỗi sai trích dẫn phải cọc một khoản `stakeAmount`.
   - Áp dụng cơ chế bỏ phiếu Commit-Reveal để hội đồng giám khảo phân xử theo mô hình Schelling Point.
   - Nếu bắt lỗi đúng: Trả thưởng + hoàn cọc. Nếu báo cáo rác: Slash 100% tiền cọc.
3. **Đóng gói & Kiểm toán Hệ thống**:
   - Đóng gói toàn bộ nền tảng bằng Docker Compose với cấu hình Production.
   - Chạy kiểm toán bảo mật với Slither, đạt chuẩn an toàn 100%.

#### Tiêu chí Nghiệm thu (Acceptance Criteria)
- [ ] Toàn bộ chu trình từ: Nhận câu hỏi -> Thu phí x402 -> Định tuyến Multi-Agent -> Hybrid RAG -> NLI Guardrail -> Sinh biên lai Salted Provenance -> Batching Merkle Root lên Base L2 hoạt động trơn tru tự động 100%.
- [ ] Thử nghiệm thành công kịch bản nộp khiếu nại báo lỗi ảo giác, phân xử và kích hoạt giải ngân quỹ thưởng / trừng phạt slashing tự động trên Smart Contract.
- [ ] Toàn bộ tài liệu hướng dẫn vận hành, API specs và script kiểm thử được hoàn thiện đầy đủ.

---

## 10. PHỤ LỤC TÀI NGUYÊN, CÔNG CỤ VÀ TIÊU CHUẨN ĐÁNH GIÁ (APPENDIX & TOOLING)

### 10.1. Bộ công cụ phát triển khuyến nghị (Recommended Toolchain)

| Phân hệ | Công cụ khuyến nghị | Phiên bản | Mục đích sử dụng |
|---|---|---|---|
| **Ngôn ngữ AI Backend** | Python | 3.11+ | Hiệu năng cao, hỗ trợ cú pháp gõ tĩnh tiên tiến |
| **Quản lý gói & môi trường** | Poetry / UV | Mới nhất | Quản lý phụ thuộc cô lập, giải quyết xung đột gói cực nhanh |
| **Web API Framework** | FastAPI | 0.110+ | Bất đồng bộ (`async`), tích hợp OpenAPI và Pydantic v2 |
| **Điều phối Tác tử** | LangGraph & LangChain | 0.2+ | Xây dựng đồ thị tác tử có chu trình và quản lý bộ nhớ |
| **Cơ sở dữ liệu Vector** | ChromaDB / Qdrant | Mới nhất | Lưu trữ và tìm kiếm vector nhúng đa chiều |
| **Cơ sở dữ liệu Quan hệ** | PostgreSQL | 16+ | Lưu trữ lịch sử phiên hội thoại (`PostgresSaver`) và biên lai |
| **Phát triển Smart Contract** | Foundry (Forge/Anvil/Cast) | Mới nhất | Biên dịch siêu tốc, Fuzz testing bằng Solidity thuần |
| **Kiểm toán Bảo mật Contract** | Slither & Aderyn | Mới nhất | Phân tích tĩnh phát hiện lỗ hổng bảo mật hợp đồng thông minh |
| **Tương tác EVM Client** | Viem (TS) / Web3.py (Py) | Mới nhất | Ký số EIP-712 và giao tiếp RPC Node |
| **Ảo hóa & Triển khai** | Docker & Docker Compose | Mới nhất | Đóng gói môi trường đồng nhất từ dev đến production |

---

### 10.2. Danh mục Mạng thử nghiệm (Testnet Environments) & RPC Endpoints

- **Base Sepolia Testnet**:
  - Chain ID: `84532`
  - Tiền tệ: `ETH` (Sepolia test ETH)
  - Public RPC: `https://sepolia.base.org`
  - Block Explorer: `https://sepolia.basescan.org`
  - Faucet: [faucets.chain.link](https://faucets.chain.link/) hoặc Coinbase Developer Faucet.
- **Arbitrum Sepolia Testnet**:
  - Chain ID: `421614`
  - Tiền tệ: `ETH` (Arbitrum Sepolia test ETH)
  - Public RPC: `https://sepolia-rollup.arbitrum.io/rpc`
  - Block Explorer: `https://sepolia.arbiscan.io`

---

### 10.3. Bảng Kiểm Tra Năng Lực Tự Đánh Giá (Self-Assessment Checklist)

Trước khi tốt nghiệp từng chặng học tập, học viên tự đối soát danh mục năng lực sau:

- [ ] **Chặng 1**:
  - [ ] Tôi có thể giải thích chi tiết cơ chế Reducer trong LangGraph giải quyết xung đột trạng thái thế nào.
  - [ ] Tôi có thể viết Regex hoặc AST parser bóc tách chính xác Điều, Khoản, Điểm từ văn bản luật Việt Nam.
  - [ ] Tôi đã tự tay tích hợp `PostgresSaver` để lưu trữ lịch sử hội thoại cho agent.
- [ ] **Chặng 2**:
  - [ ] Tôi hiểu vì sao BM25 tiếng Việt bắt buộc phải qua khâu bẻ từ (word segmentation) thay vì tách khoảng trắng.
  - [ ] Tôi tính toán được bằng tay điểm số RRF của một tài liệu từ 2 danh sách xếp hạng khác nhau.
  - [ ] Tôi giải thích được nguyên lý mô hình Cross-Encoder và cơ chế gác cổng NLI Entailment.
- [ ] **Chặng 3**:
  - [ ] Tôi có thể trình bày cấu trúc Domain Separator trong EIP-712 và giải thích tại sao nó chống được Replay Attack.
  - [ ] Tôi đã lập trình và thực thi thành công một giao dịch ủy quyền EIP-3009 trên mạng Base Sepolia.
  - [ ] Tôi sử dụng thành thạo `forge test --fuzz-runs 1000` để kiểm định tính bất biến của hợp đồng.
- [ ] **Chặng 4**:
  - [ ] Tôi có thể giải thích thuật toán Merkle Proof và cách hàm `verify` trong OpenZeppelin hoạt động trên EVM.
  - [ ] Tôi hiểu vì sao phải dùng Salted Commitment để bảo vệ quyền riêng tư câu hỏi của người dùng theo Nghị định 13.
  - [ ] Tôi có thể phân tích cơ chế Điểm Schelling được áp dụng trong hệ thống tòa án phân xử Kleros thế nào.

---

*Tài liệu được biên soạn và bảo chứng bởi Nhóm Chuyên gia Kỹ thuật Hệ thống Trust-AGENT. Mọi nội dung đều được đối soát thực tế với codebase và các tiêu chuẩn công nghiệp hiện hành.*
