# Translation-of-GTNH

## GTNH 2.9.0 简体中文增量补丁

2026-11-01

下载：[v2.9.0.1 Release](https://github.com/Itsusinn/Translation-of-GTNH/releases/tag/v2.9.0.1)。适用于 `GT_New_Horizons_2.9.0_Java_17-26.zip` 对应的官方 2.9.0 整合包。

官方已有的汉化作为运行和校验基线，不复制进本仓库或补丁包。补丁只提供 1,350 个不同于官方的语言条目，以及一份中文语法规则：

- 补齐 853 个缺失语言键，翻译 403 个英文占位条目。
- 恢复 73 条已有中文译文，修复血魔法“图符”手册的重复键与三页错位。
- 保留原补丁的 18 条名称校正及魔晶语法规则。

不再打包官方完整任务书、模组语言文件、GregTech 材料语言文件、加载提示、界面配置或 408 篇官方中文文档。包含校正的模组语言文件也只保留差异键，安装到独立的 TX Loader 强制加载路径，保留官方完整文件。

## 安装

将 `GTNH-2.9.0-zh_CN.zip` 解压到官方 2.9.0 实例的 `.minecraft` 目录，合并 `config` 文件夹。本增量包不替换官方包已有文件。

如果安装过此前的全量补丁，请先恢复官方语言资源和配置，再安装增量版；直接叠加不会自动清除旧包残留。自己修改过的汉化文件请先备份。

官方汉化与增量补丁合并后，任务书覆盖 7,720/7,720 个语言键。此数字不是本包新增译文数量，也不代表所有游戏文本均已翻译。血魔法故事书等既有英文内容仍有保留，游戏内显示尚未实测。

## 更新、验证和打包

需要 Python 3.11 或更高版本，无第三方依赖。在仓库根目录执行：

```powershell
python scripts/update_modpack_translation.py ../GT_New_Horizons_2.9.0_Java_17-26.zip --sync --build
```

脚本读取官方包用于比对，按 `scripts/corrections-2.9.0.json` 生成差量校正，保留新增补译、名称校正及语法规则，并移除资源目录中的全量副本。不会把官方汉化导入仓库。

去掉 `--sync` 可验证现有增量内容；添加 `--build` 在验证通过后打包。检查包括语言覆盖、格式参数、重复语言键、官方同值条目和官方文件覆盖。输出位于 `dist`，包含 ZIP、SHA-256 和 `validation.json`。

`scripts/patch-manifest-2.9.0.json` 记录校验过的差量文件及其哈希。发布工作流执行 `python scripts/build_release.py` 从标签源码打包；未校验的新文件或内容变化会停止打包，防止重新混入官方资源。已有完整校验后可直接使用此命令，无需再次下载官方整合包。

## 主要汉化者有：

`Kiwi` 剩下的所有工作

`MuXiu1997` 版本更新自动化比对脚本、PT推送脚本、自动化打包脚本、自动化每日构建脚本

`ChromicRedBrick` 任务书校对、汉化

`Sky_Cat` 任务书初步汉化

`huajijam` 校对GregTech.lang、汉化GT++mod、汉化魔法蜜蜂魔导手册

`BloCamLimb` 修改完善任务书config生成脚本

`JackMeds` 汉化标题画面

`YPXxiao` GTNH介绍文本汉化

`Wired` 语言文件提取脚本

`albus12138` GT++手册汉化工具

`iouter` 添加并汉化未能本地化的流体词条

`wumingzhiren` igi血魔法逗号分割


所有在PT上参与汉化工作的[贡献者](https://paratranz.cn/projects/4964/members)


以及老版本翻译主要贡献者

`anti`翻译GregTech.lang

`Yesterday`汉化任务书及构建框架

`TOCN`、`doctormdk`早期版本任务书汉化

另外，由于许多汉化都是在模组自带汉化基础上完善的，所以无法得知作者，只能在此一并感谢所有为汉化工作作出过贡献的人们！

## 汉化采用协议

汉化部分采用 CC-BY-NC-SA 协议

## 最后

欢迎更多的人参与到汉化工作中
