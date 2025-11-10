from PIL import Image
import io
 #注意文件格式转换为cpu密集操作，而io操作不是
 #输入原始字节流 返回png格式字节流
 #异步用法 配合await asyncio.to_thread适用，此用法适用于cpu密集型，使当前主线程进行协程的同时(此时await语句的操作很有可能吃不到cpu)，创建新线程去执行此操作，相当于多了个只执行此操作的线程
async  def verify(data: bytes):
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()                                                                                            #这里说明，不同格式的文件在字节流层面就已经有了差别
        return True
    except Exception as e:
        return False




def convert(data: bytes):
    img = Image.open(io.BytesIO(data))
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, "PNG")
    return buf.getvalue()




