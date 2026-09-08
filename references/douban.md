# 豆瓣抓取 — rexxar 移动版 API（免登录、免验证码）

豆瓣桌面版（movie.douban.com）对无 Cookie 请求直接返回"异常请求"反爬页；Firecrawl 也只能抓到 JS 占位符"加载中…"。**正确路径是移动端内部 API（rexxar）**，豆瓣 App / m.douban.com 在用，只需两个请求头，无需登录。

## 必备请求头

```
User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1
Referer: https://m.douban.com/movie/subject/{subject_id}/
```

不带 Referer 会 400，这点必须带上。

## 端点速查（subject_id 例：1293182 = 十二怒汉）

| 用途 | 端点 | 返回 |
|------|------|------|
| 影评列表（按有用数排序） | `https://m.douban.com/rexxar/api/v2/movie/{id}/reviews?start=0&count=5&sort=hotest` | JSON: `reviews[]` |
| 单篇影评全文 | `https://m.douban.com/rexxar/api/v2/review/{review_id}` | JSON: `content` 字段（HTML） |
| 短评（热门优先） | `https://m.douban.com/rexxar/api/v2/movie/{id}/interests?start=0&count=8&sort=score` | JSON: `interests[]` |

subject_id 从电影页 URL 取：`movie.douban.com/subject/1293182/` → `1293182`。

## 字段说明

**reviews[]**（影评列表）：
- `title` / `abstract`（摘要）/ `useful_count`（有用数 → 按 `sort=hotest` 已排好序）
- `rating.value`（作者评分 1-5）/ `author.name` / `id`（单篇全文用）/ `url`

**review/{id}**（单篇全文）：
- 正文在 **`content`** 字段（HTML，需剥标签）——注意不是 `text`，也没有 `text` 字段
- 其余：`title` / `abstract` / `useful_count` / `user.name` / `comments_count`

**interests[]**（短评）：
- `comment`（短评文本）/ `vote_count`（赞数）/ `rating.value`（星级）/ `user.name`

## PowerShell 实操模板

```powershell
$headers = @{
  'User-Agent' = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
  'Referer'    = 'https://m.douban.com/movie/subject/1293182/'
}
$r = Invoke-WebRequest -Uri 'https://m.douban.com/rexxar/api/v2/movie/1293182/reviews?start=0&count=5&sort=hotest' -Headers $headers -UseBasicParsing
$j = $r.Content | ConvertFrom-Json
$j.reviews | ForEach-Object { $_.title + ' | 有用:' + $_.useful_count + ' | id:' + $_.id }
```

## 踩坑记录（实测）

1. **`/comments` 端点已失效（404）**——短评要用 `/interests`，不要用 `/comments`。
2. **单篇全文正文在 `content` 字段**，不是 `text`；误取 `text` 得到空字符串且不报错。
3. 桌面版 `movie.douban.com/subject/.../reviews` 无 Cookie 请求 → 返回字节数组形式的"异常请求"页（Invoke-WebRequest 不报错但内容是反爬页，检查字节数 <4KB 即可识别）。
4. Firecrawl 抓豆瓣影评页只返回"加载中…"占位符（JS 渲染），别浪费时间。
5. PS 5.1 下 `ForEach-Object` 直接 Out-Host 输出中文可能丢字/空行异常 → 先拼 `StringBuilder` 再 `[IO.File]::WriteAllText(path, s, [Text.Encoding]::UTF8)` 落盘，然后 read_file。
6. `start`/`count` 翻页：`start=5&count=5` 取第 6-10 篇；`sort=hotest`（影评）/ `sort=score`（短评热门）。
7. 请求头缺少 `Referer` → 400 Bad Request；UA 换成桌面 Chrome 也可能被拒，保持 iPhone UA。
