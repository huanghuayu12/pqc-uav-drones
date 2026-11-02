# 投稿前必须填的占位符

**当前剩余 28 处，全部是作者信息**（作者块 12、作者贡献 15、资助 1）。
仓库地址与可选的 `\firstnote` 已处理完毕，见第四节。

MDPI 不会带占位符送排版，这一份是把它们列成可以一次填完的表。
填好发我，或者直接按行号替换。

## 一、作者块（12 处，`main.tex` 第 59–80 行）

模板默认是**三位作者、单一单位**。作者人数不同的话要改结构，先告诉我。

| # | 行 | 占位符 | 需要的内容 | 示例 |
|---|---|---|---|---|
| 1 | 59 | `<<Name>>` | 学术编辑姓名 | 通常留空，由编辑部填 |
| 2 | 69 | `<<Given Name>>` | 第一作者全名 | `Wei Zhang` |
| 3 | 69 | `<<Given Name>>` | 第二作者全名 | `Li Chen` |
| 4 | 70 | `<<Given Name>>` | 第三作者全名（通讯） | `Hao Liu` |
| 5 | 72 | `<<First A.>>` | 第一作者缩写名 | `Wei Zhang` |
| 6 | 72 | `<<Second B.>>` | 第二作者缩写名 | `Li Chen` |
| 7 | 72 | `<<Third C.>>` | 第三作者缩写名 | `Hao Liu` |
| 8 | 75 | `<<Department, ...>>` | 单位全称、城市、邮编、国家 | `School of Aeronautics, X Univ., Beijing 100191, China` |
| 9 | 76 | `<<e-mail@1>>` | 第一作者邮箱 | |
| 10 | 76 | `<<e-mail@2>>` | 第二作者邮箱 | |
| 11 | 78 | `<<e-mail@3>>` | 通讯作者邮箱（可与 #10 相同） | |
| 12 | 80 | `<<if applicable>>` | 现地址；**没有就整行删掉** | |

补充两个模板支持、当前未用的字段：

- `\orcid{...}`：想挂 ORCID 就给我 16 位号，投稿系统也会单独收
- `\firstnote{}`：只有第一作者有"现地址"时才需要

## 二、作者贡献（15 处，`main.tex` 第 1937–1942 行）

模板用 A / B / C 指代三位作者，现在 15 个占位标记的分布是：
**A 出现 7 次、B 5 次、C 3 次**。

给我一句话分工就行，例如"张构思和主写，陈做实验和作图，刘指导"，
我按 CRediT 术语填进现有句式。默认句式是：

```
Conceptualization, A; methodology, A and B; software, B; validation, A;
formal analysis, A; investigation, A and B; data curation, B;
writing—original draft preparation, A; writing—review and editing, A and C;
visualization, B; supervision, C; project administration, C.
```

如果分工不同（比如两人共同第一作者），告诉我，我改句式而不只是换字母。

## 三、资助（1 处，第 1945 行）

```
\funding{<<This research received no external funding.>>}
```

- 无资助：把 `<<>>` 去掉，保留原句
- 有资助：给我**基金号 + 资助方全称**，MDPI 要求写全称，例如
  `This work was supported by the National Natural Science Foundation of China (grant no. 62xxxxxx).`

## 四、仓库地址 —— 已完成

仓库已建并推送：**https://github.com/huanghuayu12/pqc-uav-drones**

- 账号 `huanghuayu12`，SSH key 已配置（`~/.ssh/id_ed25519`），后续可直接 `git push`
- 提交作者已设为 `huanghuayu12 <huanghuayu12@users.noreply.github.com>`，贡献图会计入
- 远程 `main` 与本地同步，最新提交 `189e08d`
- 正文 `\dataavailability` 已改为该 URL，PDF 文本层已核实渲染正确
- `\firstnote`（现地址）整行删除，因为它是可选项，留占位会被排版退回

以后更新数据的流程：

```
cd pqc-uav-drones
python run_all.py          # 重跑实验，覆盖 results/
git add -A && git commit -m "说明"
git push
```

想给论文一个比裸 URL 更稳的引用，可以再花十分钟上 Zenodo：
用 GitHub 账号登录 https://zenodo.org → Settings → GitHub → 打开本仓库开关 →
在 GitHub 上发一个 Release → Zenodo 自动生成 DOI。拿到 DOI 告诉我，
我把 `\dataavailability` 改成 DOI 引用。

## 五、填完之后我做什么

1. 替换剩余 28 处，`grep -o "<<[^>]*>>"` 归零
2. 重新编译，确认 0 overfull / 0 error / 41 标签齐全
3. 出终稿 PDF，并核对页眉的作者名与 `\AuthorNames` 一致
4. 打包投稿材料：正文 PDF、7 张矢量图（`manuscript/*.pdf`）、
   `RESPONSE-2.md`、cover letter（需要的话我一并写）
