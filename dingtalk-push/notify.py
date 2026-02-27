import sys, time, hmac, hashlib, base64, urllib.parse, requests, json, os, argparse

# 从环境变量读取配置（必须配置）
WEBHOOK = os.environ.get("DINGTALK_WEBHOOK", "")
SECRET = os.environ.get("DINGTALK_SECRET", "")

# 图床配置
# 优先使用 imgbb，需要注册获取 API 密钥：https://api.imgbb.com/
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "")
# 备用图床（敖武的图床）
BACKUP_IMAGE_HOST = "https://playground.z.wiki/img-cloud/upload"

def check_config():
    """检查必要配置是否存在"""
    if not WEBHOOK:
        print("错误：未配置 DINGTALK_WEBHOOK 环境变量", file=sys.stderr)
        sys.exit(1)
    if not SECRET:
        print("错误：未配置 DINGTALK_SECRET 环境变量", file=sys.stderr)
        sys.exit(1)

def get_sign():
    """生成钉钉签名"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = SECRET.encode('utf-8')
    string_to_sign = f'{timestamp}\n{SECRET}'.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign

def send_markdown(content, title="消息通知"):
    """发送 Markdown 消息"""
    timestamp, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={timestamp}&sign={sign}"
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": content
        }
    }
    resp = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    return resp.json()

def send_link(title, text, pic_url, message_url):
    """发送 Link 消息（带图片预览）"""
    timestamp, sign = get_sign()
    url = f"{WEBHOOK}&timestamp={timestamp}&sign={sign}"
    data = {
        "msgtype": "link",
        "link": {
            "title": title,
            "text": text,
            "picUrl": pic_url,
            "messageUrl": message_url
        }
    }
    resp = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    return resp.json()

def send_image_with_markdown(image_path, caption=""):
    """
    上传图片并发送 Markdown 消息
    支持本地图片路径或 URL
    """
    # 如果是 URL，直接使用
    if image_path.startswith("http://") or image_path.startswith("https://"):
        image_url = image_path
    else:
        # 本地图片，上传到图床
        if not os.path.exists(image_path):
            return {"error": f"图片文件不存在: {image_path}"}
        
        print(f"正在上传图片: {image_path}", file=sys.stderr)
        
        # 尝试 imgbb 图床（优先）
        if IMGBB_API_KEY:
            image_url = upload_to_imgbb(image_path)
        else:
            image_url = None
        
        # 如果 imgbb 失败，尝试备用图床
        if not image_url:
            print("imgbb 上传失败或未配置 API 密钥，尝试备用图床...", file=sys.stderr)
            image_url = upload_to_backup_host(image_path)
        
        if not image_url:
            # 所有图床都失败，发送描述性消息
            print("所有图床上传失败，发送描述性消息", file=sys.stderr)
            file_size = os.path.getsize(image_path) / 1024  # KB
            file_name = os.path.basename(image_path)
            md_content = f"**图片上传失败**\n\n文件: {file_name}\n大小: {file_size:.1f}KB\n路径: {image_path}\n\n请检查图床配置或手动上传。"
            if caption:
                md_content = f"{caption}\n\n{md_content}"
            return send_markdown(md_content, title="图片消息（上传失败）")
        
        print(f"图片上传成功: {image_url}", file=sys.stderr)
    
    # 构建 Markdown 内容
    md_content = f"![图片]({image_url})"
    if caption:
        md_content = f"{caption}\n\n{md_content}"
    
    return send_markdown(md_content, title=caption or "图片消息")

def upload_to_imgbb(image_path):
    """上传图片到 imgbb 图床"""
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            data = {'key': IMGBB_API_KEY}
            resp = requests.post('https://api.imgbb.com/1/upload', files=files, data=data, timeout=30)
            result = resp.json()
            
            if result.get("success"):
                return result["data"]["url"]
            else:
                print(f"imgbb 上传失败: {result.get('error', {}).get('message', '未知错误')}", file=sys.stderr)
                return None
    except Exception as e:
        print(f"imgbb 上传异常: {e}", file=sys.stderr)
        return None

def upload_to_backup_host(image_path):
    """上传图片到备用图床（敖武的图床）"""
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            resp = requests.post(BACKUP_IMAGE_HOST, files=files, timeout=30)
            
            # 尝试解析响应
            try:
                result = resp.json()
                if result.get("success") or result.get("url"):
                    return result.get("url") or result.get("data", {}).get("url")
            except:
                # 如果不是 JSON，尝试从 HTML 中提取 URL
                if resp.status_code == 200:
                    # 这里需要根据实际响应调整
                    print("备用图床返回非JSON响应，可能已变更", file=sys.stderr)
            
            return None
    except Exception as e:
        print(f"备用图床上传异常: {e}", file=sys.stderr)
        return None

def main():
    check_config()  # 检查配置
    
    parser = argparse.ArgumentParser(description="钉钉消息推送工具")
    parser.add_argument("--image", "-i", help="图片路径或URL，发送图片消息")
    parser.add_argument("--caption", "-c", default="", help="图片说明文字")
    parser.add_argument("--link", "-l", nargs=4, metavar=("TITLE", "TEXT", "PIC_URL", "MSG_URL"),
                        help="发送 Link 消息: 标题 描述 图片URL 跳转URL")
    parser.add_argument("--title", "-t", default="消息通知", help="消息标题")
    
    args = parser.parse_args()
    
    # 发送图片消息
    if args.image:
        result = send_image_with_markdown(args.image, args.caption)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    # 发送 Link 消息
    if args.link:
        title, text, pic_url, msg_url = args.link
        result = send_link(title, text, pic_url, msg_url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    # 默认：从标准输入读取 Markdown 内容
    content = sys.stdin.read().strip()
    if content:
        result = send_markdown(content, args.title)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("错误：请通过标准输入传入内容，或使用 --image/--link 参数", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()