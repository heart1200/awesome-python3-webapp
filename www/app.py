#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Luodayu'

import aiohttp

'''
async web application.
'''

import logging

logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time
from aiohttp import web


async def index(request):
    return web.Response(text="<h1>Awesome</h1>", content_type='text/html')


async def init(loops):
    # 创建webapp对象app
    app = web.Application(loop=loops)
    app.router.add_routes([web.get('/', index)])
    app_runner = web.AppRunner(app)
    await app_runner.setup()
    srv = web.TCPSite(app_runner, '127.0.0.1', 9000)
    await srv.start()
    logging.info('server started at http://127.0.0.1:9000...')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()

# async def handle(request):
#     """
#     处理请求的函数
#     """
#     return web.Response(text="<h1>Awesome</h1>", content_type='text/html')
#
#
# async def serve_static_file(request):
#     """
#     处理静态文件请求的函数
#     """
#     # 文件路径从请求对象中获取
#     file_path = request.match_info['path']
#     if not os.path.exists(file_path):
#         # 如果文件不存在，则返回404响应
#         return web.Response(status=404)
#
#     # 如果文件存在，则设置响应头并返回文件内容
#     with open(file_path, 'rb') as f:
#         content = f.read()
#     content_type = aiohttp.hdrs.MIME_TYPES.get(os.path.splitext(file_path)[1], 'application/octet-stream')
#     return web.Response(body=content, content_type=content_type)
#
#
# async def handle_form(request):
#     """
#     处理表单提交请求的函数
#     """
#     data = await request.post()
#     return web.Response(text='Hello, {}!'.format(data['name']))
#
#
# async def handle_json(request):
#     """
#     处理JSON API请求的函数
#     """
#     data = await request.json()
#     response_data = {'message': 'Hello, {}!'.format(data['name'])}
#     return web.json_response(response_data)
#
#
# async def create_server():
#     """
#     创建和启动服务器的函数
#     """
#     # 创建应用对象
#     app = web.Application()
#
#     # 注册路由处理程序
#     app.router.add_get('/', handle)
#     app.router.add_static('/static', 'static')
#     app.router.add_get('/form', lambda r: web.FileResponse('form.html'))
#     app.router.add_post('/form', handle_form)
#     app.router.add_post('/json', handle_json)
#
#     # 创建服务器
#     runner = web.AppRunner(app)
#     await runner.setup()
#     site = web.TCPSite(runner, '127.0.0.1', 9000)
#
#     # 启动服务器
#     await site.start()
#     print('Server started at http://127.0.0.1:9000')
#
#
# if __name__ == '__main__':
#     asyncio.run(create_server())
