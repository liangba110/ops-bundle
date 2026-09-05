# 服务器A（42.193.113.230）项目清单

## 1. 同途搭子主站
- 功能：旅游搭子平台（需求发布/预约交易/评价/置顶/公众号对接）
- 前台：www.ttdazi.xyz / dazi.openai2000.cn
- 后端：api.openai2000.cn（端口5002，Flask）
- 管理后台：dazi.openai2000.cn/op-{随机路径}（路径每日轮换）
- 数据库：huizhiyun（40+表）
- 管理员：admin / ops_admin
- 代码：/opt/ttdazi/

## 2. 独立支付微服务
- 功能：微信Native/JSAPI支付、回调处理、订单结算
- 地址：pay.openai2000.cn（端口5005）
- 商户号：1114539763
- 代码：/opt/ttdazi/payment_service/

## 3. AI智能建站
- 功能：零代码AI建站（模板/组件/预览/发布到B服务器）
- 前台：aiweb.openai2000.cn
- 后端：端口5003（Flask）
- 数据库：aiweb（8张表）
- AI模型：DeepSeek
- 站点存放：/opt/aiweb/sites
- 部署目标：Server B（82.157.202.24）/var/www/aiweb-sites
- 代码：/opt/aiweb/

## 4. 软件授权API
- 功能：多软件登录/充值/VIP授权管理
- 主站：softapi.openai2000.cn
- 管理后台：softapi.openai2000.cn/admin/
- 后端：端口5006（FastAPI）
- 数据库：software_auth（8张表）
- 管理员：admin
- 代码：/opt/software_auth/
- GitHub：liangba110/software_auth_api

## 5. 汇智云VPS全自动运维
- 功能：30模块智能运维（检测/事件/学习/预测/修复/告警）
- 代码：/opt/ttdazi/ops/（34个Python模块）
- 运行方式：crontab（15个定时任务）
- GitHub：liangba110/ops-bundle

## 通用信息
- MySQL：root / huizhiyun2026
- Redis：127.0.0.1:6379
- Caddy反代：443端口统一入口
- 1Panel面板：/opt/1panel
- 数据盘：/data/disk（20G，16%使用）
- 系统盘：69G，53%使用
