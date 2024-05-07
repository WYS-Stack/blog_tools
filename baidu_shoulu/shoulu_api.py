import re

import requests


class SL:
    def __init__(self, site, token, sitemap_xml):
        self.site = site
        self.token = token
        self.sitemap_xml = sitemap_xml

    def get_bokeurl(self):
        with open(self.sitemap_xml, "r") as f:
            data = f.read()
        urls = re.findall(r'<loc>(.+?)</loc>', data, re.S)
        print(f">>> 读取网站地图共有网页链接数 ：{len(urls)} 条!")
        return urls

    def get_site_map(self):
        response = requests.get(url=self.sitemap_xml)
        urls = re.findall('<loc>(.*?)</loc>', response.text)
        return urls

    def api(self):
        # sitemap.xml是链接时
        if "http" in self.sitemap_xml:
            urls = self.get_site_map()
        # sitemap.xml是文件时
        else:
            urls = self.get_bokeurl()
        post_url = f'http://data.zz.baidu.com/urls?site={self.site}&token={self.token}'
        headers = {
            'User-Agent': 'curl/7.12.1',
            'Host': 'data.zz.baidu.com',
            'Content-Type': 'text/plain',
            'Content-Length': '83'
        }
        response = requests.post(post_url, headers=headers, data='\n'.join(urls))
        if response.status_code == 200:
            data = response.json()
            # 推送成功的次数
            len_url = data.get('success')
            # 剩余的推送次数
            remain_url = data.get('remain')
            # 不是本站的url
            not_same_site_urls = data.get("not_same_site")
            # 不合法的url
            not_valid_urls = data.get("not_valid_url")
            print(f"成功推送的url共：{len_url}")
            print(f"当天剩余的可推送url条数：{remain_url}")
            print(f'由于不是本站url而未处理的url列表：{not_same_site_urls}')
            print(f'不合法的url列表：{not_valid_urls}')

        else:
            # 推送失败信息
            print(response.json())


if __name__ == '__main__':
    site = "https://www.cherain-wh.cloud"
    token = "E7afv32wEopEGIYH"
    # 本地的sitemap.xml
    sitemap_xml = "/Users/wanghan/Desktop/code/blog/public/sitemap.xml"
    # # 网站上的sitemap.xml
    # sitemap_xml = "https://www.cherain-wh.cloud/sitemap.xml"
    sl = SL(site=site, token=token, sitemap_xml=sitemap_xml)  # sitemap_xml 网站或本地 选一种
    sl.api()
