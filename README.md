# Blogger Editorial Theme

一个为个人博客设计的 Blogger 响应式主题，现用于 [rinuan.org](https://rinuan.org)。整体采用温暖、克制的编辑排版风格，支持中英双语、简繁切换、深色模式，并内置可交互的博客看板娘。

## 主要特性

- 响应式布局，适配桌面端与移动端
- 自动跟随系统的浅色 / 深色外观，并记住用户选择
- 中文 / English 界面切换
- 简体 / 繁体中文转换
- 根据文章标签自动调整中英文排版
- 文章阅读时间、阅读进度和返回顶部功能
- 相关文章、评论区、文章分页与标签导航
- Open Graph 与 Twitter Card 分享信息
- 自定义 404 页面
- 针对键盘导航、减少动态效果和打印场景的无障碍优化
- 可拖动、缩放、隐藏并保存偏好的交互式看板娘

## 文件结构

```text
.
├── theme.xml                         # Blogger 主题文件
├── README.md                         # 项目说明
└── mascot/
    ├── README.md                     # 看板娘素材说明
    ├── CLAUDE_INTEGRATION_PROMPT.md  # 素材集成参考提示词
    ├── blog-mascot.png               # 原始角色插画
    ├── chibi/                         # 网页版角色与探头素材
    ├── emotions/                      # 网页版表情素材
    ├── chibi-hd/                      # 高分辨率角色素材
    └── emotions-hd/                   # 高分辨率表情素材
```

## 安装

1. 登录 [Blogger](https://www.blogger.com/) 并进入目标博客。
2. 打开 **主题** 页面，先通过 **备份** 下载当前主题。
3. 点击 **恢复**，上传本仓库根目录中的 `theme.xml`。
4. 打开博客，检查首页、文章页、标签页、评论区和 404 页面。
5. 在 Blogger 的 **布局** 页面配置博客标题、描述、标签菜单和社交链接。

> 上传主题会替换博客当前的主题代码。已有文章不会被删除，但建议始终先备份当前主题。

## 配置

### 博客信息

博客标题与描述读取自 Blogger 的站点设置，无需直接修改 XML。

### 导航菜单

导航由 Blogger 标签组件生成，并默认包含首页、中文和英文入口。其他文章标签会自动加入菜单。如需调整固定入口，可在 `theme.xml` 中搜索 `main-nav`。

### 社交链接

页脚社交链接位于 `footer-social-section` 中。发布前请搜索 `Social Media Links`，将其中的个人主页地址替换为自己的链接。

### 分享封面

没有题图的文章和非文章页面会使用默认分享封面。搜索 `cover-light.png` 即可替换其地址，推荐图片尺寸为 `1200 × 630`。

### 看板娘

看板娘素材默认通过 jsDelivr 从以下目录加载：

```text
https://cdn.jsdelivr.net/gh/rinuuan/blog-assets@main/mascot/chibi
```

角色支持拖动、吸边、闲置探头、尺寸调节、对话级别设置、隐藏和重新唤出；相关偏好保存在浏览器的 `localStorage` 中。素材规格和目录说明见 [`mascot/README.md`](mascot/README.md)。

若要使用自己的素材，请保持透明 PNG、相同文件名及一致的画布比例，或同步修改 `theme.xml` 中的 `BASE` 地址和对应文件名。

### 配色与排版

主题颜色、内容宽度及玻璃面板效果集中定义在 `theme.xml` 的 `:root` 和 `[data-theme="dark"]` 变量中。常用变量包括：

```css
--bg-color
--text-color
--meta-color
--accent-color
--border-color
--container-width
```

主题使用 Google Fonts 提供的 `Inter`、`EB Garamond` 和 `Dancing Script`，中文优先使用系统字体。

## 外部依赖

主题不需要构建工具，但运行时会使用以下外部服务：

- Blogger 模板与评论系统
- Google Fonts
- jsDelivr CDN（看板娘素材及简繁转换脚本）
- Blogger JSONP Feed（相关文章）

如所在网络无法访问这些服务，对应字体、简繁转换、看板娘或相关文章功能可能不可用，但文章主体仍可正常显示。

## 发布前检查

- 确认 XML 能由 Blogger 正常上传并保存
- 替换默认分享封面和页脚社交链接
- 分别检查中文、英文、简体和繁体显示
- 检查浅色、深色及移动端布局
- 检查文章图片、代码块、评论和相关文章
- 检查看板娘素材是否能从 CDN 正常加载
- 使用无痕窗口确认首次访问体验

## 许可

Copyright © 2026 rinuuan，保留版权。

- 主题代码与文档采用 [PolyForm Noncommercial 1.0.0](LICENSES/PolyForm-Noncommercial-1.0.0.txt)
- `mascot/` 中的角色图片采用 [CC BY-NC 4.0](LICENSES/CC-BY-NC-4.0.txt)

两份许可证均允许符合条款的非商业使用、修改和再分发。再分发时须保留相应版权、许可证及署名声明；商业使用须另行获得书面授权。具体适用范围见根目录的 [`LICENSE`](LICENSE)。

由于包含非商业用途限制，该许可证属于源码可用许可证，不是 [OSI](https://opensource.org/osd) 定义下的开源许可证。
