# step8_mcp_client.py
# 第 8 步:写一个 MCP 客户端,去连 step7 那个服务端,并【真的调用工具拿到结果】。
#
# ======================================================================
# 这一步要干 5 件事(连起来就是一次完整的 MCP 通信)
# ----------------------------------------------------------------------
#   1. 把 step7 服务端作为一个【子程序】启动起来;
#   2. 通过 stdio(那对"传话筒")跟它接上;
#   3. 握手对暗号(initialize);
#   4. 问它"你有哪些工具?"(list_tools)—— 工具【自动发现】;
#   5. ★真的点一道菜:调用 get_weather,把天气结果打印出来(call_tool)。
#
# 还没接大模型。这一步只验证"客户端 ↔ 服务端"能跑通,并拿到真实返回。
# (下一步 step9 再把模型接进来,让模型自己决定调哪个工具。)
#
#   关系图:
#     step8(客户端)  --启动并连接-->  step7(服务端,提供 get_weather / get_peopletotal)
#     step8 问:"有啥工具?"          <--  step7 答:"这俩"
#     step8 说:"调 get_weather(北京)" -->  step7 执行,把结果传回
# ======================================================================


# ======================================================================
# 第 1 部分:导入
# ======================================================================

# 【Python 基础:asyncio】异步的"总开关",step6b 早餐小程序里见过。
import asyncio

# 【Python 基础:Path】安全地拼文件路径,step5 用过。
from pathlib import Path

# 【MCP 概念:客户端要用的三样东西】
#   ClientSession         —— 一次"会话"。握手、列工具、调工具,都通过它。
#   StdioServerParameters —— 一张"上岗说明单":写清楚怎么把服务端启动起来。
#   stdio_client          —— 真正负责"启动服务端 + 架好那对传话筒管道"的函数。
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ======================================================================
# 第 2 部分:异步主函数
# ======================================================================

# 【Python 基础:async def】定义一个"可以中途暂停、去等慢操作"的函数。
#   下面凡是要"等服务端"的地方,都会用 await。
async def run_mcp_client() -> None:
    """连上 step7 天气服务端,发现工具并真的调用一次。"""

    # ------------------------------------------------------------------
    # 2.1 算出几个关键路径
    # ------------------------------------------------------------------
    # 【Python 基础:__file__ / .resolve() / .parent】
    #   __file__   = 当前这个文件自己的路径
    #   .resolve() = 补成完整的绝对路径
    #   .parent    = 它所在的文件夹(也就是 myagent)
    project_directory = Path(__file__).resolve().parent

    # Path 对象可以用 / 来拼下一层(这不是除法,是 Path 专门的拼路径写法)。
    # 拼出虚拟环境里的 python.exe,和 step7 服务端文件。
    python_executable = project_directory.parent / ".venv" / "Scripts" / "python.exe"   # .venv 在根目录(上一层)
    server_file = project_directory / "step7_weather_mcp_server.py"

    # 【工程习惯:先验证,别带着错往下跑】
    #   启动前先确认这两个文件真的在,不在就立刻报一句看得懂的话。
    if not python_executable.exists():
        raise FileNotFoundError(f"找不到虚拟环境的 Python:{python_executable}")
    if not server_file.exists():
        raise FileNotFoundError(f"找不到 MCP 服务端文件:{server_file}")

    # ------------------------------------------------------------------
    # 2.2 写好"怎么启动服务端"的说明单
    # ------------------------------------------------------------------
    # 【MCP 概念:stdio 模式下,是客户端负责把服务端当子程序启动的】
    #   打个比方:你(客户端)雇个厨子,把菜谱本(step7)塞给他,让他去后厨开火待命。
    #   StdioServerParameters 就是给厨子的"上岗说明单":
    #       command = 用哪个程序去跑   → .venv 里的 python.exe
    #       args    = 给它哪个文件去跑 → step7_weather_mcp_server.py
    #   合起来 ≈ 在命令行执行:  .venv\Scripts\python.exe step7_weather_mcp_server.py
    #   (还记得 step7 的 if __name__=="__main__" 吗?正是被这样【直接运行】,服务才真启动。)
    #   str(...) 是因为这里要的是普通字符串,而 python_executable 是 Path 对象。
    server_parameters = StdioServerParameters(
        command=str(python_executable),
        args=[str(server_file)],
    )

    print("正在启动服务端并建立连接……")

    # ------------------------------------------------------------------
    # 2.3 启动服务端 + 架好传话筒(第一层 async with)
    # ------------------------------------------------------------------
    # 【Python 基础:async with —— 就是你 step4 见过的 with 的异步版】
    #   step4 查天气写过:  with urllib.request.urlopen(...) as response:
    #   with 的作用是:【进去时自动打开,出来时自动关好】一个资源,
    #   你不用手动记着关 —— 哪怕中途报错,它也保证帮你收尾。
    #   async with 一模一样,只是用在【异步资源】上。
    #
    #   stdio_client(...) 一进来就把服务端子程序启动起来,并给你两根管道:
    #       read_stream  = 客户端用它【读】服务端发来的消息
    #       write_stream = 客户端用它【写】消息给服务端
    async with stdio_client(server_parameters) as (read_stream, write_stream):

        # --------------------------------------------------------------
        # 2.4 把两根管道包装成一次"会话"(第二层 async with)
        # --------------------------------------------------------------
        # 有了 ClientSession,后面就不用自己手搓协议消息,
        # 直接调 initialize() / list_tools() / call_tool() 这些清楚的方法。
        async with ClientSession(read_stream, write_stream) as client_session:

            # ----------------------------------------------------------
            # 2.5 握手对暗号
            # ----------------------------------------------------------
            # 【MCP 概念:握手】第一次连上,双方先确认"用哪版协议、各自支持啥"。
            #   await = 在这儿等握手完成,再往下走。
            await client_session.initialize()
            print("握手成功,已经连上服务端!\n")

            # ----------------------------------------------------------
            # 2.6 自动发现:问服务端"你有哪些工具?"
            # ----------------------------------------------------------
            # 【MCP 概念:工具自动发现】—— 这正是 MCP 比手写 function calling 爽的地方:
            #   客户端不用提前知道有啥工具,问一句就拿到完整清单(名字+说明+参数表)。
            tools_response = await client_session.list_tools()
            discovered_tools = tools_response.tools   # 真正的工具列表在 .tools 里

            print(f"发现了 {len(discovered_tools)} 个工具:")
            for discovered_tool in discovered_tools:
                print(f"  · {discovered_tool.name}:{discovered_tool.description}")
            print()

            # ----------------------------------------------------------
            # 2.7 ★重点★ 真的点一道菜:调用工具,拿到结果
            # ----------------------------------------------------------
            # 【MCP 概念:list_tools 只是"看菜单",call_tool 才是"真点菜"】
            #   第一个参数:工具名(字符串)
            #   第二个参数:参数字典(对应 step7 里 get_weather 的 city)
            print("调用 get_weather(city=北京)……")
            weather_call_result = await client_session.call_tool(
                "get_weather",
                {"city": "北京"},
            )

            # 【MCP 概念:返回结果为什么裹了好几层?】
            #   call_tool 返回的不是一句纯文字,而是一个"结果对象"。
            #   真正的文字在 .content 这个【列表】里(取第 0 个元素的 .text)。
            #   为什么用列表?因为 MCP 工具允许一次返回好几块内容(多段文字、甚至图片),
            #   所以统一用列表装。我们这里只有一段文字,取 [0].text 就行。
            weather_text = weather_call_result.content[0].text
            print(f"  服务端返回:{weather_text}\n")

            # 再点另一道菜,证明两个工具都通。
            print("调用 get_peopletotal(city=北京)……")
            population_call_result = await client_session.call_tool(
                "get_peopletotal",
                {"city": "北京"},
            )
            population_text = population_call_result.content[0].text
            print(f"  服务端返回:{population_text}\n")

            # Windows 终端可能使用 GBK 编码。为保证所有环境都能稳定打印，
            # 这里不用箭头、emoji 等非必要特殊字符。
            print("MCP 客户端和服务端全程跑通!")


# ======================================================================
# 第 3 部分:按下异步总开关
# ======================================================================
# 【Python 基础:asyncio.run】async def 函数不能直接调用就跑,
#   必须用 asyncio.run(...) 启动:开事件循环 → 跑完 → 关掉。
if __name__ == "__main__":
    asyncio.run(run_mcp_client())
