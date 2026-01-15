import os
import json
import re
from typing import Dict, List, Any, Optional
import logging
import aiohttp
import time
import ssl

logger = logging.getLogger(__name__)

# SSL配置：开发环境可以禁用SSL验证（仅用于开发，生产环境应使用有效证书）
# 设置环境变量 DISABLE_SSL_VERIFY=true 来禁用SSL验证
DISABLE_SSL_VERIFY = os.getenv("DISABLE_SSL_VERIFY", "false").lower() == "true"

if DISABLE_SSL_VERIFY:
    logger.warning("⚠️ [SSL] SSL证书验证已禁用（仅用于开发环境）")
    # 创建不验证SSL证书的上下文
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
else:
    ssl_context = None  # 使用默认SSL上下文（验证证书）

class AIAnalyzer:
    """使用ChatGPT-5 API进行交易分析"""
    
    def __init__(self):
        # 从环境变量获取API token（与参考代码保持一致）
        self.api_key = os.getenv("AI_BUILDER_TOKEN", "")
        self.model = "gpt-5"  # 使用gpt-5模型
        # 使用AI Builder Space作为ChatGPT API的中转站
        # 参考代码格式：base_url + "/v1/chat/completions"
        self.base_url = "https://space.ai-builders.com/backend"
        self.chat_url = f"{self.base_url}/v1/chat/completions"
    
    async def analyze_trades_with_ai(self, trades_data: List[Dict[str, Any]], capital_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """使用ChatGPT-5分析交易数据（通过AI Builder Space中转）"""
        logger.info("=" * 80)
        logger.info("🤖 [ChatGPT-5] 开始AI交易分析")
        logger.info("=" * 80)
        
        # 检查Token配置
        if not self.api_key:
            logger.warning("⚠️ [ChatGPT-5] AI_BUILDER_TOKEN未设置，使用基础分析")
            logger.warning("💡 [ChatGPT-5] 提示: 请在.env文件中配置AI_BUILDER_TOKEN以启用ChatGPT-5分析")
            return self._basic_analysis(trades_data)
        
        logger.info(f"🔑 [ChatGPT-5] Token状态: ✅ 已配置")
        logger.info(f"🌐 [ChatGPT-5] API端点: {self.chat_url}")
        logger.info(f"🤖 [ChatGPT-5] 模型: {self.model}")
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 构建分析提示（包含所有交易数据和备注）
            logger.info("📝 [ChatGPT-5] 正在构建分析提示...")
            prompt = self._build_analysis_prompt(trades_data, capital_history)
            prompt_length = len(prompt)
            
            logger.info(f"📊 [ChatGPT-5] 数据统计:")
            logger.info(f"   • 交易记录数: {len(trades_data)}条")
            logger.info(f"   • 资金曲线数据: {len(capital_history) if capital_history else 0}条")
            logger.info(f"   • 提示词长度: {prompt_length}字符")
            
            # 统计交易数据详情
            if trades_data:
                closed_trades = [t for t in trades_data if t.get('status') == 'closed']
                win_trades = [t for t in trades_data if t.get('profit', 0) > 0]
                logger.info(f"   • 已平仓交易: {len(closed_trades)}条")
                logger.info(f"   • 盈利交易: {len(win_trades)}条")
                logger.info(f"   • 亏损交易: {len(trades_data) - len(win_trades)}条")
            
            # 创建ClientSession，配置SSL上下文
            connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
            async with aiohttp.ClientSession(connector=connector) as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # 标准OpenAI API格式的payload（与参考代码保持一致）
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": """你是一位资深的A股交易分析师和资金管理专家，拥有丰富的实战经验。

你的任务是：
1. 深入挖掘交易数据背后的真实问题
2. 发现交易者的痛点和薄弱环节
3. 提供犀利、直接、实用的分析和建议
4. 不要被数据表面现象迷惑，要看到本质问题

分析风格：
- 直击要害，不回避问题
- 用数据说话，但也要有洞察力
- 发现模式、趋势和异常
- 提供可执行的改进建议

请用中文回答，语言要专业但易懂，分析要深入且实用。"""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 1.0,  # 创造性参数（gpt-5固定为1.0）
                    "max_tokens": 3000  # 最大响应长度（使用max_tokens，与参考代码一致）
                }
                
                logger.info("=" * 80)
                logger.info("📤 [ChatGPT-5] ========== 发送API请求 ==========")
                logger.info("=" * 80)
                logger.info(f"🌐 [ChatGPT-5] 请求URL: {self.chat_url}")
                logger.info(f"📋 [ChatGPT-5] 请求参数:")
                logger.info(f"   • Model: {payload['model']}")
                logger.info(f"   • Temperature: {payload['temperature']}")
                logger.info(f"   • Max Tokens: {payload['max_tokens']}")
                logger.info("")
                logger.info("=" * 80)
                logger.info("📥 [ChatGPT-5] ========== 输入数据 (System Message) ==========")
                logger.info("=" * 80)
                logger.info(payload['messages'][0]['content'])
                logger.info("")
                logger.info("=" * 80)
                logger.info("📥 [ChatGPT-5] ========== 输入数据 (User Message/Prompt) ==========")
                logger.info("=" * 80)
                logger.info(f"📏 [ChatGPT-5] Prompt长度: {len(payload['messages'][1]['content'])}字符")
                logger.info("")
                logger.info(payload['messages'][1]['content'])
                logger.info("")
                logger.info("=" * 80)
                logger.info("📤 [ChatGPT-5] ========== 请求发送中... ==========")
                logger.info("=" * 80)
                
                request_start = time.time()
                
                async with session.post(
                    self.chat_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as response:
                    request_time = time.time() - request_start
                    
                    logger.info(f"📥 [ChatGPT-5] 收到API响应")
                    logger.info(f"📥 [ChatGPT-5] HTTP状态码: {response.status}")
                    logger.info(f"⏱️ [ChatGPT-5] 请求耗时: {request_time:.2f}秒")
                    
                    if response.status == 200:
                        result = await response.json()
                        ai_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # 解析响应详情
                        usage = result.get("usage", {})
                        total_tokens = usage.get("total_tokens", 0)
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)
                        
                        total_time = time.time() - start_time
                        
                        logger.info("=" * 80)
                        logger.info("✅ [ChatGPT-5] ========== AI分析成功！==========")
                        logger.info("=" * 80)
                        logger.info(f"📊 [ChatGPT-5] 响应统计:")
                        logger.info(f"   • HTTP状态码: {response.status}")
                        logger.info(f"   • 响应长度: {len(ai_response)}字符")
                        logger.info(f"   • 总Token数: {total_tokens}")
                        logger.info(f"   • 提示Token: {prompt_tokens}")
                        logger.info(f"   • 完成Token: {completion_tokens}")
                        logger.info(f"⏱️ [ChatGPT-5] 请求耗时: {request_time:.2f}秒")
                        logger.info(f"⏱️ [ChatGPT-5] 总耗时: {total_time:.2f}秒")
                        logger.info("")
                        logger.info("=" * 80)
                        logger.info("📤 [ChatGPT-5] ========== 输出数据 (AI完整响应) ==========")
                        logger.info("=" * 80)
                        logger.info(ai_response)
                        logger.info("")
                        logger.info("=" * 80)
                        logger.info("🔄 [ChatGPT-5] ========== 数据流向追踪 ==========")
                        logger.info("=" * 80)
                        logger.info("📥 输入:")
                        logger.info(f"   • 交易记录数: {len(trades_data)}条")
                        logger.info(f"   • 资金曲线数据: {len(capital_history) if capital_history else 0}条")
                        logger.info(f"   • Prompt长度: {len(prompt)}字符")
                        logger.info(f"   • 提示Token: {prompt_tokens}")
                        logger.info("")
                        logger.info("🌐 API调用:")
                        logger.info(f"   • 端点: {self.chat_url}")
                        logger.info(f"   • 模型: {self.model}")
                        logger.info(f"   • 状态: ✅ 成功 (HTTP {response.status})")
                        logger.info("")
                        logger.info("📤 输出:")
                        logger.info(f"   • AI响应长度: {len(ai_response)}字符")
                        logger.info(f"   • 完成Token: {completion_tokens}")
                        logger.info(f"   • 响应预览: {ai_response[:300]}...")
                        logger.info("")
                        logger.info("=" * 80)
                        
                        # 解析AI响应
                        logger.info("🔄 [ChatGPT-5] 正在解析AI响应...")
                        parsed_result = self._parse_ai_response(ai_response, trades_data)
                        logger.info("✅ [ChatGPT-5] 响应解析完成")
                        logger.info(f"📋 [ChatGPT-5] 解析结果字段数: {len(parsed_result)}")
                        logger.info("=" * 80)
                        return parsed_result
                    else:
                        error_text = await response.text()
                        total_time = time.time() - start_time
                        
                        logger.error("=" * 80)
                        logger.error(f"❌ [ChatGPT-5] API请求失败")
                        logger.error(f"❌ [ChatGPT-5] HTTP状态码: {response.status}")
                        logger.error(f"❌ [ChatGPT-5] 错误详情: {error_text[:500]}")
                        logger.error(f"⏱️ [ChatGPT-5] 失败耗时: {total_time:.2f}秒")
                        logger.error("=" * 80)
                        
                        return self._basic_analysis(trades_data)
                        
        except aiohttp.ClientError as e:
            total_time = time.time() - start_time
            logger.error("=" * 80)
            logger.error(f"❌ [ChatGPT-5] 网络连接错误")
            logger.error(f"❌ [ChatGPT-5] 错误类型: {type(e).__name__}")
            logger.error(f"❌ [ChatGPT-5] 错误详情: {str(e)}")
            logger.error(f"⏱️ [ChatGPT-5] 失败耗时: {total_time:.2f}秒")
            logger.error("=" * 80)
            return self._basic_analysis(trades_data)
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error("=" * 80)
            logger.error(f"❌ [ChatGPT-5] AI分析失败")
            logger.error(f"❌ [ChatGPT-5] 错误类型: {type(e).__name__}")
            logger.error(f"❌ [ChatGPT-5] 错误详情: {str(e)}")
            logger.error(f"⏱️ [ChatGPT-5] 失败耗时: {total_time:.2f}秒")
            logger.error("=" * 80, exc_info=True)
            return self._basic_analysis(trades_data)
    
    def _build_analysis_prompt(self, trades_data: List[Dict[str, Any]], capital_history: Optional[List[Dict]] = None) -> str:
        """构建AI分析提示"""
        # 计算基础统计
        total_trades = len(trades_data)
        win_trades = sum(1 for t in trades_data if t.get('profit', 0) > 0)
        lose_trades = total_trades - win_trades
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        
        profits = [t.get('profit', 0) for t in trades_data]
        total_profit = sum(profits)
        avg_profit = sum(p for p in profits if p > 0) / max(win_trades, 1) if win_trades > 0 else 0
        avg_loss = abs(sum(p for p in profits if p < 0) / max(lose_trades, 1)) if lose_trades > 0 else 0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
        
        # 分析止损止盈设置
        stop_loss_prices = [t.get('stop_loss_price') for t in trades_data if t.get('stop_loss_price')]
        take_profit_prices = [t.get('take_profit_price') for t in trades_data if t.get('take_profit_price')]
        stop_loss_executed = sum(1 for t in trades_data if t.get('order_result') == '止损')
        take_profit_executed = sum(1 for t in trades_data if t.get('order_result') == '止盈')
        
        # 分析入场价格
        buy_prices = [t.get('buy_price', 0) for t in trades_data if t.get('buy_price')]
        avg_buy_price = sum(buy_prices) / len(buy_prices) if buy_prices else 0
        
        # 计算止损止盈比例
        stop_loss_ratios = []
        take_profit_ratios = []
        for t in trades_data:
            if t.get('buy_price') and t.get('stop_loss_price'):
                ratio = abs((t['stop_loss_price'] - t['buy_price']) / t['buy_price'] * 100)
                stop_loss_ratios.append(ratio)
            if t.get('buy_price') and t.get('take_profit_price'):
                ratio = abs((t['take_profit_price'] - t['buy_price']) / t['buy_price'] * 100)
                take_profit_ratios.append(ratio)
        
        avg_stop_loss_ratio = sum(stop_loss_ratios) / len(stop_loss_ratios) if stop_loss_ratios else 0
        avg_take_profit_ratio = sum(take_profit_ratios) / len(take_profit_ratios) if take_profit_ratios else 0
        
        # 资金管理分析
        capital_info = ""
        if capital_history:
            capitals = [h.get('capital', 0) for h in capital_history]
            if capitals:
                initial_capital = capitals[0] if capitals else 100000
                current_capital = capitals[-1] if capitals else 100000
                capital_change = current_capital - initial_capital
                capital_change_pct = (capital_change / initial_capital * 100) if initial_capital > 0 else 0
                capital_info = f"""
## 资金管理数据
- 初始资金: {initial_capital:.2f}元
- 当前资金: {current_capital:.2f}元
- 资金变化: {capital_change:+.2f}元 ({capital_change_pct:+.2f}%)
- 资金曲线: {json.dumps([{'date': str(h.get('date', '')), 'capital': h.get('capital', 0)} for h in capital_history[-30:]], ensure_ascii=False)}
"""
        
        prompt = f"""
# 交易数据分析任务

## 数据概览
- 总交易次数: {total_trades}
- 盈利交易: {win_trades} | 亏损交易: {lose_trades}
- 胜率: {win_rate:.2f}%
- 累计盈亏: {total_profit:+.2f}元
- 平均盈利: {avg_profit:.2f}元 | 平均亏损: {avg_loss:.2f}元
- 盈亏比: {profit_loss_ratio:.2f}
- 止损执行: {stop_loss_executed}次 | 止盈执行: {take_profit_executed}次
- 平均止损比例: {avg_stop_loss_ratio:.2f}% | 平均止盈比例: {avg_take_profit_ratio:.2f}%
{capital_info}

## 完整交易记录（包含所有字段和备注）
{json.dumps(trades_data[:20], ensure_ascii=False, indent=2)}

---

# 分析任务

请深入分析这些交易数据，**发现真实的问题和痛点**。不要被表面数据迷惑，要挖掘深层问题。

## 核心分析方向（但不限于此）：

1. **止损止盈分析**
   - 止损止盈设置是否合理？执行情况如何？
   - 有没有明显的风险控制问题？
   - 止损止盈的执行纪律如何？

2. **入场时机分析**
   - 入场时机的选择有什么规律或问题？
   - 是否存在追高、抄底等常见错误？
   - 入场价格与后续表现的关系？

3. **盈亏比深度分析**
   - 当前盈亏比({profit_loss_ratio:.2f})是否健康？
   - 盈利交易和亏损交易有什么本质区别？
   - 如何优化盈亏比？

4. **资金管理分析**
   - 资金使用是否合理？
   - 仓位管理有什么问题？
   - 资金曲线的变化说明了什么？

5. **交易痛点挖掘**（重点）
   - **发现交易者最严重的问题是什么？**
   - **哪些交易习惯是致命的？**
   - **最大的风险点在哪里？**
   - **最需要改进的地方是什么？**

## 分析要求：

- **直击要害**：不要回避问题，直接指出痛点
- **数据支撑**：用具体数据说明问题
- **发现模式**：找出交易中的规律和异常
- **可执行建议**：提供具体、可操作的改进方案
- **深度洞察**：不只是描述现象，要分析原因

## 输出格式：

请以JSON格式返回，但内容要深入、犀利、实用：

{{
  "stop_loss_analysis": "止损止盈的深度分析，指出问题和改进方向（至少200字，要犀利）",
  "take_profit_analysis": "止盈策略的分析，发现痛点和优化空间（至少200字，要实用）",
  "entry_price_analysis": "入场时机的深度分析，找出问题和规律（至少200字，要深入）",
  "profit_loss_ratio_analysis": "盈亏比的全面分析，发现问题和优化方案（至少200字，要具体）",
  "capital_management": "资金管理的深度分析，指出风险和改进建议（至少300字，要可执行）",
  "key_insights": [
    "核心洞察1：发现的关键问题或规律（至少50字，要犀利）",
    "核心洞察2：发现的交易痛点或模式（至少50字，要深入）",
    "核心洞察3：发现的风险点或机会（至少50字，要实用）"
  ],
  "recommendations": [
    "具体建议1：可执行的改进措施（至少50字，要明确）",
    "具体建议2：需要改变的交易习惯（至少50字，要直接）",
    "具体建议3：风险控制或策略优化（至少50字，要可操作）"
  ]
}}

**重要**：不要只是重复数据，要**发现问题和痛点**，提供**有价值的洞察**！
"""
        return prompt
    
    def _parse_ai_response(self, ai_response: str, trades_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """解析AI响应"""
        try:
            # 尝试提取JSON（支持多行JSON）
            json_match = re.search(r'\{[\s\S]*\}', ai_response)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                # 验证必需字段
                required_fields = [
                    "stop_loss_analysis", "take_profit_analysis", "entry_price_analysis",
                    "profit_loss_ratio_analysis", "capital_management", "key_insights", "recommendations"
                ]
                for field in required_fields:
                    if field not in parsed:
                        parsed[field] = ""
                return parsed
        except Exception as e:
            logger.error(f"解析AI响应失败: {e}")
            logger.debug(f"AI响应内容: {ai_response[:500]}")
        
        # 如果解析失败，返回基础分析
        return self._basic_analysis(trades_data)
    
    def _basic_analysis(self, trades_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """基础分析（当AI不可用时）"""
        if not trades_data:
            return {
                "stop_loss_analysis": "暂无交易数据，无法进行止损价格分析。建议在首次交易时设置止损价格为买入价的3-5%。",
                "take_profit_analysis": "暂无交易数据，无法进行止盈价格分析。建议设置止盈价格为买入价的6-10%，确保盈亏比≥2:1。",
                "entry_price_analysis": "暂无交易数据，无法进行入场价格分析。建议在技术分析确认趋势后入场，避免追高。",
                "profit_loss_ratio_analysis": "暂无交易数据，无法进行盈亏比分析。建议目标盈亏比>1.5，理想>2.0。",
                "capital_management": "建议先进行小额交易，积累经验。单笔交易不超过总资金的10%，总风险不超过总资金的2%。",
                "key_insights": ["暂无交易记录，开始您的第一笔交易吧！"],
                "recommendations": ["建议先进行小额交易，积累经验", "设置合理的止损止盈价格", "严格执行交易纪律"]
            }
        
        # 计算基础统计
        profits = [t.get('profit', 0) for t in trades_data]
        buy_prices = [t.get('buy_price', 0) for t in trades_data if t.get('buy_price')]
        stop_loss_prices = [t.get('stop_loss_price', 0) for t in trades_data if t.get('stop_loss_price')]
        take_profit_prices = [t.get('take_profit_price', 0) for t in trades_data if t.get('take_profit_price')]
        
        win_trades = [p for p in profits if p > 0]
        lose_trades = [p for p in profits if p < 0]
        avg_profit = sum(win_trades) / len(win_trades) if win_trades else 0
        avg_loss = abs(sum(lose_trades) / len(lose_trades)) if lose_trades else 0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
        
        stop_loss_executed = sum(1 for t in trades_data if t.get('order_result') == '止损')
        take_profit_executed = sum(1 for t in trades_data if t.get('order_result') == '止盈')
        
        return {
            "stop_loss_analysis": f"平均止损价格设置: {sum(stop_loss_prices)/len(stop_loss_prices):.2f}元。已执行止损{stop_loss_executed}次。建议止损比例控制在3-5%，严格执行止损纪律。" if stop_loss_prices else "未设置止损价格。建议设置止损价格为买入价的3-5%，保护资金安全。",
            "take_profit_analysis": f"平均止盈价格设置: {sum(take_profit_prices)/len(take_profit_prices):.2f}元。已执行止盈{take_profit_executed}次。建议止盈比例控制在6-10%，确保盈亏比≥2:1。" if take_profit_prices else "未设置止盈价格。建议设置止盈价格为买入价的6-10%，确保盈亏比≥2:1。",
            "entry_price_analysis": f"平均入场价格: {sum(buy_prices)/len(buy_prices):.2f}元。共{buy_prices.__len__()}笔交易。建议在技术分析确认趋势后入场，避免追高。" if buy_prices else "无入场价格数据。",
            "profit_loss_ratio_analysis": f"当前盈亏比: {profit_loss_ratio:.2f}。平均盈利{avg_profit:.2f}元，平均亏损{avg_loss:.2f}元。{'盈亏比健康' if profit_loss_ratio >= 1.5 else '盈亏比偏低，建议提高止盈目标或降低止损幅度'}。",
            "capital_management": f"建议单笔交易不超过总资金的10%，总风险不超过总资金的2%。当前盈亏比{profit_loss_ratio:.2f}，{'表现良好' if profit_loss_ratio >= 1.5 else '需要优化'}。严格执行止损止盈，控制仓位规模。",
            "key_insights": [
                f"盈亏比: {profit_loss_ratio:.2f}",
                f"止损执行: {stop_loss_executed}次，止盈执行: {take_profit_executed}次"
            ],
            "recommendations": [
                "严格执行止损止盈纪律",
                "控制单笔交易资金占比≤10%",
                "目标盈亏比>1.5"
            ]
        }

# 全局实例
ai_analyzer = AIAnalyzer()
