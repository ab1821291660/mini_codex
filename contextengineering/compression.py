"""上下文压缩的触发与执行 —— context engineering 的收口点。
把"每轮调模型前,历史太长就先压缩(总结式压缩 + 保留首尾)"这件事收在这里:
主循环只调用 maybe_compress(),不用关心阈值判断、summarizer 注入和提示打印。
真正的压缩策略(保留首尾 + 中段总结)在 History.compress() 里。
"""
import json
import config
class ContextCompressor:
    def __init__(self, client,model):
        # client 需提供 summarize(text) -> str,用来把中段历史压成摘要
        self._client = client
        self._model = model


    def summarize(self, text: str) -> str:
        """把一段 agent 工作记录压缩成要点。供 History.compress() 注入使用。
        独立的一次 LLM 调用,不带工具。"""
        messages = [
            {
                "role": "system",
                "content": (
                    "你是对话摘要助手。把下面的 agent 工作记录压缩成简洁要点,"
                    "务必保留:做过哪些操作、读/改了哪些文件(含文件名)、关键结论。"
                    "不要编造,只总结已发生的内容。"
                ),
            },
            {"role": "user", "content": text},
        ]
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages
        )
        return resp.choices[0].message.content or ""


    def _estimated_tokens(self, messages: list[dict]) -> int:
        """估算整个历史的 token 数(零依赖近似,不追求和 GLM 分词器逐字一致)。
        规则:中日韩字符约 1 token/字;其余字符约 1 token / 4 字符。"""
        text = json.dumps(messages, ensure_ascii=False, default=str)
        cjk = other = 0
        for ch in text:
            # CJK 表意文字 + 中日韩标点/假名/谚文,按 1 字 ≈ 1 token 估
            if "一" <= ch <= "鿿" or "　" <= ch <= "ヿ" or "가" <= ch <= "힣":
                cjk += 1
            else:
                other += 1
        return cjk + other // 4
    # def maybe_compress(self, messages: list[dict]) -> bool:
    #     """每轮调模型前调用:历史太长就触发总结式压缩(保留首尾)。
    #     真的压缩了返回 True 并打印提示,否则返回 False。"""
    #     if self.compress(self.summarize):
    #         print("[上下文压缩] 历史过长,已把早前对话总结成摘要。")
    #         return True
    #     return False
    def maybe_compress(self, _messages: list[dict]) -> bool:##传入的summarizer为方法函数
        """总结式压缩 + 保留首尾。触发并压缩了返回 True,否则 False。
        三个约束:
          ① 头(system + 首条 user 任务)保留,尾(最近 KEEP_TAIL 条)保留,中段总结。
          ② 总结要调一次LLM —— summarizer当参数注入,History不绑定具体模型。
          ③ 按"完整轮次"切:尾部起点若是孤立的 tool 结果,往前挪到拥有它的
             assistant,绝不拆散 tool_call 与 tool 结果的配对。
        """
        if self._estimated_tokens(_messages) <= config.COMPRESS_THRESHOLD_TOKENS:
            return False
        msgs = _messages
        head_n = config.KEEP_HEAD
        # 太短就不值得压(头 + 尾 + 1 条摘要都装不下)
        if len(msgs) <= head_n + config.KEEP_TAIL + 1:
            return False


        # 约束③:确定尾部起点,并保证它不是孤立的 tool 结果
        start = len(msgs) - config.KEEP_TAIL
        while start > head_n and msgs[start].get("role") == "tool":##===================================
            start -= 1  # 往前挪,把发起这些 tool 调用的 assistant 一起纳入尾部


        head = msgs[:head_n]##===================================#中间的 head = _messages[:head_n] 这类切片会产生新列表,但那只是临时变量,不影响 _messages 本身的身份。
        middle = msgs[head_n:start]##===================================
        tail = msgs[start:]##===================================
        if not middle:
            return False
        # 约束②:把中段交给 summarizer 总结(这一步真正调一次模型)
        summary = self.summarize(_render(middle))##===================================
        # 摘要用 user 角色注入:OpenAI 兼容接口对 user 消息位置最宽容,最不容易报错
        summary_msg = {
            "role": "user",
            "content": f"[以下是早前对话的摘要,供你参考]\n{summary}",
        }
        # 原地改写传入的列表,让调用方持有的同一引用看到压缩结果 #maybe_compress 只依赖传入的 _messages,不再依赖任何未初始化的实例状态。
        # 改为 _messages[:] = head + [summary_msg] + tail,原地改写切片,这样调用方持有的同一引用就能看到压缩后的结果。
        # 是切片赋值,原地替换列表内容,对象 id 不变。压缩结果会真正反映回 self.history._messages,history.get() 下一轮拿到的就是压缩后的历史。##===================================##===================================##===================================
        _messages[:] = head + [summary_msg] + tail##===================================##===================================##===================================
        return True
def _render(messages) -> str:
    """把一段消息拼成可读文本,喂给 summarizer 去总结。
    工具结果可能很长,截断到 500 字符,避免摘要输入本身又爆掉。"""
    lines = []
    for m in messages:
        role = m.get("role")
        if role == "user":##===================================
            lines.append(f"用户: {m.get('content', '')}")
        elif role == "assistant":##===================================
            for tc in m.get("tool_calls") or []:
                fn = tc["function"]
                lines.append(f"助手调用工具 {fn['name']}({fn['arguments']})")
            if m.get("content"):
                lines.append(f"助手: {m['content']}")
        elif role == "tool":##===================================
            lines.append(f"工具结果: {str(m.get('content', ''))[:500]}")
    return "\n".join(lines)