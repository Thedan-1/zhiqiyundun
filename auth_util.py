#!/usr/bin/env python
# encoding: utf:8

import random
import string
import time
import hashlib
import hmac
import base64
import urllib.parse
import json # 导入 json 库，虽然当前接口不需要 body 签名，但为了完整性可以保留

__all__ = ['gen_sign_headers']

# 随机字符串
def gen_nonce(length=8):
    chars = string.ascii_lowercase + string.digits
    return ''.join([random.choice(chars) for _ in range(length)])

# 生成 canonical_query_string
def gen_canonical_query_string(params):
    if params:
        # 对 key 和 value 进行 URL 编码
        encoded_params = []
        for k, v in params.items():
            # 确保 value 是字符串类型
            encoded_params.append((urllib.parse.quote(str(k)), urllib.parse.quote(str(v))))

        # 按 key 字典顺序排序
        sorted_params = sorted(encoded_params)

        # 使用 & 连接
        s = "&".join("=".join(kv) for kv in sorted_params)
        return s
    else:
        return ''

# 生成签名
def gen_signature(app_key, signing_string):
    bytes_secret = app_key.encode('utf-8')
    # 注意：文档中使用的是 HMAC-SHA256-HEX，然后进行 base64 编码
    # Python 的 hmac.new().digest() 返回的是字节串，需要先转换为十六进制字符串
    # 或者直接使用 hmac.new().hexdigest() 获取十六进制字符串
    # 文档示例中是先计算 HMAC-SHA256 的摘要，然后进行 base64 编码，所以我们使用 digest()
    hash_obj = hmac.new(bytes_secret, signing_string, hashlib.sha256)
    bytes_sig = hash_obj.digest() # 获取 HMAC-SHA256 摘要的字节串
    signature = base64.b64encode(bytes_sig).decode('utf-8') # 对摘要字节串进行 Base64 编码
    return signature

# 生成签名头部
def gen_sign_headers(app_id, app_key, method, uri, query):
    method = str(method).upper()
    timestamp = str(int(time.time()))
    nonce = gen_nonce()
    canonical_query_string = gen_canonical_query_string(query)

    # 构建 signed_headers_string
    signed_headers_string = f"x-ai-gateway-app-id:{app_id}\nx-ai-gateway-timestamp:{timestamp}\nx-ai-gateway-nonce:{nonce}"

    # 构建 signing_string
    # signing_string = HTTP Method + "\n" + HTTP URI + "\n" + canonical_query_string + "\n" + app_id + "\n" + timestamp + "\n" + signed_headers_string
    signing_string = f"{method}\n{uri}\n{canonical_query_string}\n{app_id}\n{timestamp}\n{signed_headers_string}"

    # 文档中 signing_string 需要编码为 utf-8
    signing_string_bytes = signing_string.encode('utf-8')

    signature = gen_signature(app_key, signing_string_bytes)

    # 构建请求头
    headers = {
        'X-AI-GATEWAY-APP-ID': app_id,
        'X-AI-GATEWAY-TIMESTAMP': timestamp,
        'X-AI-GATEWAY-NONCE': nonce,
        'X-AI-GATEWAY-SIGNED-HEADERS': "x-ai-gateway-app-id;x-ai-gateway-timestamp;x-ai-gateway-nonce",
        'X-AI-GATEWAY-SIGNATURE': signature
    }
    return headers