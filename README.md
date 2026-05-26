# job_spider
job_spider
# 使用方法
  pip3 install requests
  ## 抓取广州所有职位（含详情，最多 1000 条）
  python3 gd_job_spider.py --cities 广州
  ## 多城市 + 关键词，跳过详情（更快）
  python3 gd_job_spider.py --cities 广州 深圳 --keyword 工程师 --no-detail
  ## 快速测试（只抓 3 页）
  python3 gd_job_spider.py --cities 广州 --max-pages 3
  ## 抓取全省所有城市，保存到指定目录
  python3 gd_job_spider.py --all-cities --output-dir ./output

你是一个专业的爬虫工程师，请分析这个地址和访问这个地址获取到的内容：https://ggfw.hrss.gd.gov.cn/recruitment/internet/main/#/search?type=1&fromSSO=1，然后写一个爬虫脚本，这个脚本满足：
1.能抓取到设置的城市的所有职位，这职位有详情url的话，访问详情，然后抓取
2.这个职位包含职位title，标签信息，其他福利，联系电话，岗位描述，学历要求，工作经验，工作地点
