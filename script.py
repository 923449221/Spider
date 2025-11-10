#不要在循环中进行异步操作，尽量提前循环抽入方法中统一调用
# 输入的问题
#注意Semaphore只控制当前层，对于多层嵌套的任务，并不会限制作用域下的总任务数
#asyncio.to_thread 适用于cpu密集任务，相当于额外的一个线程不断运行此语句，此写法只是为了不破坏协程，直接用await，此任务运行太慢甚至可能会比之前协程总和还要慢
import asyncio
import os
import traceback
import aiohttp
import requests
from lxml import etree
from bs4 import BeautifulSoup
import convertImg
import aiofiles


async def selVerify(imgUrl,session,log,retry =0):
    #递归直到得出正确值                                                                              #注意这个retry用法，传参-1
    async with   session.get(imgUrl) as imgResp:
        data = await imgResp.read()
        if data.strip().startswith(b'<!DOCTYPE html') or data.strip().startswith(b'<html'):                                  #对于url无效返回网页进行处理
            raise NameError('url无效')
        if retry<5:
            if not await convertImg.verify(data):
                print("图片校验不通过，再次发起请求"+"   第"+str(retry)+"次")                               # 校验返回值，未通过再次发起请求
                log.put("图片校验不通过，再次发起请求"+"   第"+str(retry)+"次")
                return await selVerify(imgUrl,session,retry+1)                                                   #这里一定要加return,否则第2次递归的返回值不会返回
            else:
                print("图片校验成功")
                log.put("图片校验成功")
                return data
        else:
            raise NameError('重试次数过多,下载失败')

async def downloadImg(session, imgName,imgUrl,fileName,log):
    dir_path = f"img/{fileName}"
    imgName=imgName.split(".")[0]
    os.makedirs(dir_path, exist_ok=True)                                    #不存在目录就创建
    if os.path.isfile(dir_path + "/" + imgName.split(".")[0]+".png"):                            # 存在下载内容就跳过
        print(f"File {imgName} already exists")
        log.put(f"File {imgName} already exists")
    else:
        try:
            buff= await selVerify(imgUrl,session,log)
            data= await asyncio.to_thread(convertImg.convert,buff)
            async with aiofiles.open(dir_path+"/"+ imgName.split(".")[0]+".png", mode="wb") as f:
                await f.write(data)
            print("Downloaded " + imgName+"convert png")
            log.put("Downloaded " + imgName+"convert png")
        except aiohttp.ClientSSLError:
            print("SSL error 再次发起下载请求 ")
            log.put("SSL error 再次发起下载请求 ")
            await downloadImg(session, imgName,imgUrl,fileName,log)                                          #对于ssl错误单独进行递归处理
        except Exception as e:                                                                   #标题内url错误的图片，也要保存成空文件
            data = b""
            async with aiofiles.open(dir_path+"/"+ imgName.split(".")[0]+".png", mode="wb") as f:
                await f.write(data)
                print(f"未请求到图片内容"+"      "+traceback.format_exc())
                log.put(f"未请求到图片内容"+"      "+traceback.format_exc())


async def getImg(url, session,fileName,log):  # 具体页面每个图片
    url = url
    async with session.get(url) as resp:
        html = etree.HTML(await resp.text())
        figures = html.xpath("/html/body/div/div/main/div/div/div/article/div/figure/figure")       #建议用//figure/figure,绝对路径太愚蠢了
        tasks = []
        for fig in figures:
            imgUrl = fig.xpath("./img/@data-lazy-src")[0]
            imgName = imgUrl.split("/")[-1]
            tasks.append(asyncio.create_task(downloadImg(session, imgName,imgUrl,fileName,log)))
        await asyncio.gather(*tasks)


async def getUrl(text, session,log):
    pageNumber = []
    maxPageNum=1
    url = "https://everia.club/"
    resp = requests.get(url + "?s=" + text)
    processOne = BeautifulSoup(resp.text, "html.parser")
    pageNumbers = processOne.select("a[class='page-numbers']")  # 获取显示的几个页面
    if len(pageNumbers)==0:
        maxPageNum = 1
    else:
        for page in pageNumbers:
            num = page.text.replace(',', '')
            pageNumber.append(num)
            num=processOne.select("span[class='page-numbers current']")              # 获取当前页 因为用span包裹，所以要额外获得
            pageNumbersCurrent=num[0].text.replace(',', '')
            pageNumber.append(pageNumbersCurrent)
        maxPageNum = int(max(pageNumber,key=int))
    # 取出最大值
    tasks = []
    for i in range(1,maxPageNum+1):
        tasks.append(asyncio.create_task(getUrl2(i, session, text,log)))
    await asyncio.gather(*tasks)


async def getUrl2(number, session, text,log):
    url = "https://everia.club/"
    tasks = []
    sem=asyncio.Semaphore(1)                               #控制协程数量，此为页数协程为1，一页8个标题
    async with sem:
        async with session.get(url + "page/" + str(number) + "/?s=" + text) as resp:  # 第一个跟默认页面是一样的，不用特殊处理
            processTwo = BeautifulSoup(await resp.text(), "html.parser")
            urls = processTwo.find_all("a", class_="thumbnail-link")
            for url in urls:
                fileName = url.find("img").get("alt")
                tasks.append(asyncio.create_task(getImg(url.get("href"), session,fileName,log)))
            await asyncio.gather(*tasks)





async def everia(text,log):
    tasksOuter=[]
    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            tasksOuter.append(asyncio.create_task(getUrl(text, session,log)))
            await asyncio.gather(*tasksOuter)
    except (aiohttp.ClientError, ConnectionResetError) as e:
            await asyncio.sleep(3)
            await asyncio.gather(*tasksOuter)

    #校验损坏文件


