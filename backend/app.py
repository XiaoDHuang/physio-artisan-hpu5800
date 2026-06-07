"""
HPU 健康智能体 - Streamlit主入口

多页面应用:
1. 生理基座与身体年龄看板
2. 视觉多模态分析工坊
3. 智能体协同会诊与安全报告厅

使用方法:
    streamlit run app.py
"""

import streamlit as st
import sys
import os
import importlib

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 页面配置
st.set_page_config(
    page_title="HPU健康智能体",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    /* 隐藏Streamlit默认导航 */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    
    /* 用户卡片样式 */
    .user-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    
    /* 工作流节点样式 */
    .workflow-node {
        background: #f8f9fa;
        border: 2px solid #667eea;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        margin: 0.5rem;
    }
    
    /* 工作流箭头 */
    .workflow-arrow {
        font-size: 2rem;
        color: #667eea;
        vertical-align: middle;
    }
    
    /* 数据卡片 */
    .data-card {
        background: #e9ecef;
        border-radius: 8px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    
    /* 主标题样式 */
    .main-title {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    /* 副标题 */
    .subtitle {
        font-size: 1.2rem;
        color: #6C757D;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* 特性卡片 */
    .feature-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        transition: transform 0.3s;
        height: 100%;
    }
    .feature-card:hover {
        transform: translateY(-5px);
    }
    
    /* 评分标准表格 */
    .criteria-table {
        width: 100%;
        border-collapse: collapse;
    }
    .criteria-table th, .criteria-table td {
        border: 1px solid #ddd;
        padding: 12px;
        text-align: left;
    }
    .criteria-table th {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    .criteria-table tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    
    /* 页脚 */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #6C757D;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # 初始化session state
    if 'current_user_id' not in st.session_state:
        st.session_state.current_user_id = None
    if 'current_user_name' not in st.session_state:
        st.session_state.current_user_name = "未选择用户"
    if 'show_new_user_form' not in st.session_state:
        st.session_state.show_new_user_form = False
    
    # 侧边栏 - 用户选择
    with st.sidebar:
        st.markdown("### 🏋️ HPU健康智能体")
        st.divider()
        
        # 用户选择区
        st.markdown("#### 👤 当前用户")
        user_options = get_user_list()
        selected_user = st.selectbox(
            "选择用户",
            options=user_options,
            format_func=lambda x: x['label'],
            index=0,
            key="user_select"
        )
        
        # 新建用户按钮
        if st.button("➕ 新建用户", use_container_width=True):
            st.session_state.show_new_user_form = True
        
        # 新建用户表单
        if st.session_state.show_new_user_form:
            with st.expander("📝 创建新用户", expanded=True):
                with st.form("new_user_form"):
                    name = st.text_input("姓名", placeholder="输入姓名")
                    col1, col2 = st.columns(2)
                    with col1:
                        age = st.number_input("年龄", 10, 100, 25)
                        gender = st.selectbox("性别", ["male", "female"], format_func=lambda x: "男" if x == "male" else "女")
                    with col2:
                        height = st.number_input("身高(cm)", 100, 220, 170)
                        weight = st.number_input("体重(kg)", 30, 200, 70)
                    goal = st.selectbox("目标", ["lose_weight", "maintain", "gain_muscle"], 
                                       format_func=lambda x: {"lose_weight": "减脂", "maintain": "维持", "gain_muscle": "增肌"}.get(x, x))
                    
                    submitted = st.form_submit_button("创建", use_container_width=True)
                    if submitted and name:
                        user_id = create_user(name, age, gender, height, weight, goal)
                        if user_id:
                            st.session_state.current_user_id = user_id
                            st.session_state.show_new_user_form = False
                            st.session_state.user_created = name
                        else:
                            st.error("创建用户失败，请检查数据库连接")
                    if st.form_submit_button("取消"):
                        st.session_state.show_new_user_form = False

        # 显示创建成功消息
        if st.session_state.get("user_created"):
            st.success(f"用户 {st.session_state.user_created} 创建成功!")
            del st.session_state["user_created"]
        
        # 更新当前用户
        if selected_user and selected_user['id'] is not None:
            st.session_state.current_user_id = selected_user['id']
            st.session_state.current_user_name = selected_user['name']
        
        # 用户信息卡片
        if st.session_state.current_user_id:
            user_info = get_user_info(st.session_state.current_user_id)
            if user_info:
                st.markdown(f"""
                <div class="user-card">
                    <h4>{user_info['name']}</h4>
                    <p>年龄: {user_info['age']}岁 | {user_info['gender']}</p>
                    <p>身高: {user_info['height_cm']}cm | 体重: {user_info['weight_kg']}kg</p>
                    <p>目标: {user_info['goal']}</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        # 导航菜单
        st.markdown("#### 📍 页面导航")
        page_options = {
            "🏠 首页": "home",
            "💬 AI对话": "chat",
            "📊 生理看板": "page1",
            "👁️ 视觉工坊": "page2",
            "🧠 智能体会诊厅": "page3",
            "⚙️ 设置": "settings"
        }
        
        selected = st.radio(
            "选择页面",
            options=list(page_options.keys()),
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # 项目信息
        st.markdown("#### ℹ️ 项目信息")
        st.info("""
        **HPU健康智能体**
        
        健身 + 饮食 + 睡眠
        
        ---
        期末项目展示
        智能体多模态解决方案
        """)
        
        # 技术栈
        st.markdown("#### 🔧 技术栈")
        tech_tags = st.columns(2)
        with tech_tags[0]:
            st.markdown("""
            - Streamlit
            - LangGraph
            - MediaPipe
            """)
        with tech_tags[1]:
            st.markdown("""
            - Edge-TTS
            - Matplotlib
            - PostgreSQL
            """)
    
    # 根据选择显示页面
    if page_options[selected] == "home":
        show_home()
    elif page_options[selected] == "chat":
        page_chat = importlib.import_module("pages.4_chat_agent")
        page_chat.main()
    elif page_options[selected] == "page1":
        page1 = importlib.import_module("pages.1_physiological_dashboard")
        page1.main()
    elif page_options[selected] == "page2":
        page2 = importlib.import_module("pages.2_vision_lab")
        page2.main()
    elif page_options[selected] == "page3":
        page3 = importlib.import_module("pages.3_agent_arena")
        page3.main()
    elif page_options[selected] == "settings":
        page_settings = importlib.import_module("pages.settings_page")
        page_settings.main()


def get_user_list():
    """获取用户列表"""
    try:
        from src.database.models import get_session, User
        session = get_session()
        users = session.query(User).all()
        session.close()
        
        options = [{'id': None, 'name': '-- 选择用户 --', 'label': '-- 选择用户 --'}]
        for u in users:
            options.append({
                'id': u.id,
                'name': u.name,
                'label': f"👤 {u.name}"
            })
        return options
    except Exception as e:
        st.warning(f"数据库连接失败: {e}")
        return [{'id': None, 'name': '-- 无用户 --', 'label': '-- 无用户 --'}]


def create_user(name, age, gender, height, weight, goal):
    """创建新用户"""
    try:
        from src.database.models import get_session, User
        session = get_session()
        user = User(
            name=name,
            age=age,
            gender=gender,
            height_cm=height,
            weight_kg=weight,
            goal=goal
        )
        session.add(user)
        session.commit()
        user_id = user.id
        session.close()
        return user_id
    except Exception as e:
        st.error(f"创建用户失败: {e}")
        return None


def get_user_info(user_id):
    """获取用户详细信息"""
    try:
        from src.database.models import get_session, User
        session = get_session()
        user = session.query(User).filter_by(id=user_id).first()
        session.close()
        
        if user:
            goal_map = {
                'lose_weight': '减脂',
                'maintain': '维持',
                'gain_muscle': '增肌'
            }
            gender_map = {
                'male': '男',
                'female': '女'
            }
            return {
                'name': user.name,
                'age': user.age or 25,
                'gender': gender_map.get(user.gender, '未知'),
                'height_cm': user.height_cm or 170,
                'weight_kg': user.weight_kg or 70,
                'goal': goal_map.get(user.goal, '未知')
            }
        return None
    except:
        return None


def show_home():
    """首页"""
    # 标题
    st.markdown('<p class="main-title">🏋️ HPU 健康智能体</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Health Personal Unit | 健身 × 饮食 × 睡眠 综合管理系统</p>', unsafe_allow_html=True)
    
    # 项目概述
    st.markdown("""
    ## 📖 项目概述
    
    HPU是一个基于大语言模型的**自主智能体系统**，专注于健身、饮食和睡眠的综合健康管理。
    系统通过**函数调用(Function Calling)**实现自主决策，并结合**多模态输出**(图表+语音报告)
    提供全面的健康管理服务。
    """)
    
    # 三大核心功能
    st.markdown("## 🎯 三大核心功能")
    
    feature_col1, feature_col2, feature_col3 = st.columns(3)
    
    with feature_col1:
        st.markdown("""
        <div class="feature-card">
            <h3>📊 生理数据看板</h3>
            <p>上传华为手表JSON数据</p>
            <ul style="text-align: left; font-size: 0.9rem;">
                <li>身体准备度指数(RS)</li>
                <li>心率恢复力(HRR)</li>
                <li>多维生理雷达图</li>
                <li>Before/After对比</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with feature_col2:
        st.markdown("""
        <div class="feature-card">
            <h3>👁️ 视觉多模态分析</h3>
            <p>MediaPipe骨骼 + USDA营养</p>
            <ul style="text-align: left; font-size: 0.9rem;">
                <li>深蹲动作角度计算</li>
                <li>塌腰检测警告</li>
                <li>食物照片营养识别</li>
                <li>API真实数据调用</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with feature_col3:
        st.markdown("""
        <div class="feature-card">
            <h3>🧠 智能体会诊厅</h3>
            <p>LangGraph多Agent协同</p>
            <ul style="text-align: left; font-size: 0.9rem;">
                <li>状态机流转可视化</li>
                <li>Function Calling日志</li>
                <li>安全拦截演示</li>
                <li>Edge-TTS语音播报</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # 评分标准对照
    st.markdown("## 📋 期末项目评分标准对照")
    
    st.markdown("""
    <table class="criteria-table">
        <tr>
            <th>评分维度</th>
            <th>优秀标准 (90-100%)</th>
            <th>HPU实现</th>
        </tr>
        <tr>
            <td><b>技术复杂度</b></td>
            <td>成功实现自主规划和工具使用（函数调用）</td>
            <td>✅ LangGraph状态机 + 4个专业Agent + 真实API调用</td>
        </tr>
        <tr>
            <td><b>多模态集成</b></td>
            <td>无缝融合两种或以上模态并创造价值</td>
            <td>✅ 文本 + 雷达图/趋势图 + Edge-TTS语音</td>
        </tr>
        <tr>
            <td><b>安全与伦理</b></td>
            <td>包含针对越狱和提示注入的稳健防护</td>
            <td>✅ 双层过滤 + 正则匹配 + Llama Guard风格</td>
        </tr>
        <tr>
            <td><b>展示清晰度</b></td>
            <td>专业呈现，并清晰展示系统提示词架构</td>
            <td>✅ 3页面导航 + 状态机可视化 + 代码级展示</td>
        </tr>
    </table>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # 数据流向工作流可视化
    st.markdown("## 🔄 数据流向工作流")
    
    # 横向流程图
    workflow_cols = st.columns([1, 0.5, 1, 0.5, 1, 0.5, 1, 0.5, 1])
    
    with workflow_cols[0]:
        st.markdown("""
        <div class="workflow-node">
            <h4>📱 用户输入</h4>
            <p>手表JSON</p>
            <p>运动视频</p>
            <p>食物图片</p>
        </div>
        """, unsafe_allow_html=True)
    
    with workflow_cols[1]:
        st.markdown("<h2 style='text-align:center; color:#667eea;'>→</h2>", unsafe_allow_html=True)
    
    with workflow_cols[2]:
        st.markdown("""
        <div class="workflow-node" style="border-color:#28A745;">
            <h4>🔍 数据解析</h4>
            <p>JSON解析</p>
            <p>MediaPipe</p>
            <p>图像识别</p>
        </div>
        """, unsafe_allow_html=True)
    
    with workflow_cols[3]:
        st.markdown("<h2 style='text-align:center; color:#667eea;'>→</h2>", unsafe_allow_html=True)
    
    with workflow_cols[4]:
        st.markdown("""
        <div class="workflow-node" style="border-color:#FFC107;">
            <h4>🧠 Agent决策</h4>
            <p>状态评估</p>
            <p>计划生成</p>
            <p>安全审核</p>
        </div>
        """, unsafe_allow_html=True)
    
    with workflow_cols[5]:
        st.markdown("<h2 style='text-align:center; color:#667eea;'>→</h2>", unsafe_allow_html=True)
    
    with workflow_cols[6]:
        st.markdown("""
        <div class="workflow-node" style="border-color:#DC3545;">
            <h4>🔧 工具调用</h4>
            <p>USDA营养库</p>
            <p>wger动作库</p>
            <p>计算器</p>
        </div>
        """, unsafe_allow_html=True)
    
    with workflow_cols[7]:
        st.markdown("<h2 style='text-align:center; color:#667eea;'>→</h2>", unsafe_allow_html=True)
    
    with workflow_cols[8]:
        st.markdown("""
        <div class="workflow-node" style="border-color:#17A2B8;">
            <h4>📊 多模态输出</h4>
            <p>雷达图</p>
            <p>语音报告</p>
            <p>训练计划</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # 用户输入数据展示
    st.markdown("## 📋 支持的用户数据类型")
    
    data_col1, data_col2, data_col3 = st.columns(3)
    
    with data_col1:
        st.markdown("""
        <div class="data-card">
            <h4>⌚ 手表数据 (JSON)</h4>
            <ul>
                <li>步数 / 运动时长</li>
                <li>心率 (静息/平均/最大)</li>
                <li>HRV 指标</li>
                <li>睡眠数据</li>
                <li>压力指数</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with data_col2:
        st.markdown("""
        <div class="data-card">
            <h4>🎥 运动视频 (MP4)</h4>
            <ul>
                <li>深蹲动作分析</li>
                <li>关节角度计算</li>
                <li>塌腰检测</li>
                <li>动作质量评分</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with data_col3:
        st.markdown("""
        <div class="data-card">
            <h4>📷 食物图片 (JPG/PNG)</h4>
            <ul>
                <li>食物识别</li>
                <li>卡路里计算</li>
                <li>宏量营养素</li>
                <li>饮食平衡评估</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # 架构说明
    st.markdown("## 🏗️ 系统架构")
    
    arch_col1, arch_col2 = st.columns([1, 1])
    
    with arch_col1:
        st.markdown("""
        ### 技术栈
        
        | 层级 | 技术 | 作用 |
        |------|------|------|
        | 前端 | Streamlit | 多页面Web应用 |
        | 编排 | LangGraph | 多Agent状态机 |
        | 视觉 | MediaPipe | 骨骼关键点提取 |
        | 语音 | Edge-TTS | 神经网络语音合成 |
        | 安全 | 正则+Llama Guard | 双层安全过滤 |
        | 数据 | USDA/wger API | 真实营养动作数据 |
        """)
    
    with arch_col2:
        st.markdown("""
        ### Agent节点
        
        1. **StateEvaluator** (状态评估器)
           - 计算BMI/BMR/TDEE
           - 评估身体准备度
        
        2. **ExerciseCoach** (训练教练)
           - 制定训练计划
           - 调用wger动作库
        
        3. **NutritionPlanner** (营养规划师)
           - 计算宏量营养素
           - 调用USDA营养库
        
        4. **GuardrailAuditor** (安全审计员)
           - 审核所有输出
           - 拦截越界内容
        """)
    
    st.divider()
    
    # 快速开始
    st.markdown("## 🚀 快速开始")
    
    code_col1, code_col2 = st.columns([1, 1])
    
    with code_col1:
        st.markdown("""
        **安装依赖**
        ```bash
        pip install -r requirements.txt
        ```
        """)
    
    with code_col2:
        st.markdown("""
        **启动应用**
        ```bash
        streamlit run app.py
        ```
        """)
    
    st.info("💡 使用侧边栏导航切换到各页面进行演示")
    
    # 页脚
    st.markdown("""
    <div class="footer">
        <hr>
        <p><b>HPU 健康智能体</b> | 期末项目 - 智能体多模态解决方案</p>
        <p>健身 + 饮食 + 睡眠 | 多Agent协同 | 函数调用 | 多模态输出</p>
        <p style="color: #adb5bd;">⚠️ 本项目仅供学术演示，所有健康建议仅供参考，不构成医疗意见</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
