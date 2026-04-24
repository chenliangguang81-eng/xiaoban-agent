# 🎒 小伴 (Xiaoban Agent)

> **"不是照搬规则，而是写死价值观。"**
> 
> 专为北京市海淀区七一小学学生（小可爱）及其家长（Lion）设计的成长陪伴智能体。从小学到大学毕业，提供长达十年的全周期教育路径规划与心理陪伴。

---

## 🌟 核心定位

小伴不仅是一个问答机器人，而是一个具备**长期记忆**、**自演化能力**和**价值观护栏**的数字生命。

- **学情诊断与辅导**：苏格拉底式提问，拒绝直接给答案。
- **北京小升初全周期规划**：深度解析海淀学籍 vs 丰台户籍矛盾，提供蒙特卡洛志愿模拟。
- **张雪峰方法论集成**：将"选专业看就业，选城市看发展"的理念蒸馏为各年龄段适配的生涯规划引擎。
- **十年可持续架构**：不依赖单一 AI 模型，核心资产沉淀为本地 JSON 记忆与知识图谱。

---

## 🏗️ 架构蓝图 (v3.2)

系统采用**模型解耦与数据资产化**设计，包含四大核心引擎：

### 1. 🧠 GBrain (成长大脑)
系统的灵魂，采用本地 JSON 存储，确保十年数据不丢失。
- **基因序列图谱**：记录核心人格、学习风格、兴趣偏好。
- **知识图谱追踪**：将小学到高中的知识点构建为有向图，动态追踪掌握度。

### 2. 🔄 Phase Transition Engine (阶段跃迁引擎)
监听年级变化，自动切换小伴的"灵魂状态"：
- **小学**：简单语言，关注习惯养成与兴趣发现。
- **初中**：引入抗压陪伴，关注中考分流与学科均衡。
- **高中**：深度追问，关注高考冲刺与志愿填报。
- **大学**：平辈交流，关注考研/就业与职业规划。

### 3. 🎓 Socratic Tutor Engine (苏格拉底辅导引擎)
永远不直接给答案。引导深度随年级自动升级（深度1至深度3）。

### 4. 🧭 Career & Pathway Engine (生涯规划引擎)
深度蒸馏张雪峰方法论，贯穿十年。结合 `XiaoshengchuSimulator`（小升初志愿模拟器）与 `XiaoshengchuTimelineEngine`（备考时间轴引擎），提供落地的升学策略。

---

## 📂 目录结构 (Notion 风格)

```text
xiaoban_agent/
├── 🧠 engines/                  # 核心引擎层 (十年可持续架构)
│   ├── gbrain.py                # 成长大脑 (记忆与知识图谱)
│   ├── phase_transition_engine.py # 阶段跃迁引擎
│   ├── socratic_tutor_engine.py # 苏格拉底辅导引擎
│   ├── career_pathway_engine.py # 生涯规划引擎
│   ├── mythos_identity_engine.py# 身份稳定性引擎 (Claude Mythos)
│   ├── xiaoshengchu_simulator.py# 小升初志愿模拟器
│   ├── xiaoshengchu_timeline_engine.py # 小升初备考时间轴
│   └── xiaoshengchu_interview_coach.py # 面试准备教练
│
├── 🛠️ skills/                   # 技能模块层
│   ├── xiaoshengchu_planner.py  # 小升初规划师 (核心)
│   ├── homework_coach.py        # 作业辅导
│   ├── mistake_book.py          # 错题本 (艾宾浩斯记忆)
│   ├── zhang_xuefeng_advisor.py # 张雪峰顾问
│   └── ... (其他 5 个技能)
│
├── 📚 knowledge_base/           # 知识库层
│   ├── beijing_education_policy/# 北京教育政策 (含七一小学派位池)
│   ├── schools_database/        # 学校数据库 (23所)
│   └── zhang_xuefeng_corpus/    # 张雪峰语料库
│
├── 💾 memory/                   # 记忆存储层 (JSON 数据资产)
│   ├── memory_manager.py        # 统一记忆管理接口
│   ├── student_profile.json     # 学生画像
│   ├── knowledge_mastery.json   # 知识点掌握度
│   ├── mistake_book.json        # 错题库
│   └── ... (其他记忆文件)
│
└── 🚀 main_agent.py             # 主调度 Agent 入口
```

---

## 🚀 快速开始

### 环境要求
- Python 3.11+
- OpenAI API Key (或兼容的 LLM API)

### 运行测试
```bash
python3.11 test_integration_v2.py
```

---

## 📜 演进历史

- **v1.0**: 基础架构搭建，9大技能模块初始化。
- **v2.0**: 引入 `MemoryManager` 统一记忆层，`XiaoshengchuPlanner` 升级为 OOP 架构。
- **v3.0**: 确立"十年可持续技术架构"，实现四大核心引擎。
- **v3.1**: 深度集成 Claude Mythos 体系，引入 `MythosIdentityEngine` 确保价值观稳定性。
- **v3.2**: 增强小升初落地能力，新增志愿模拟器、时间轴引擎与面试教练。

---

*Designed by Aegis CTO & Manus AI*
