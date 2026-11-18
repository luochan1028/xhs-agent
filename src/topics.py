#!/usr/bin/env python3
"""选题生成：垂类 + 关键词 → 3 个选题；C 语言教学笔记草稿生成。

标题为句式模板改写（复用 Skill 版钩子结构，非语义生成）；
大纲为通用脚手架，须由创作者填入真实内容，不编造具体案例。
v1.1：C 语言领域用专用大纲脚手架；新增 generate_draft_note，
按主题给出一篇可直接改的笔记草稿，内嵌的代码示例均为
本地 gcc -Wall 编译通过的最小可运行程序（见 tests/test_c_domain.py）。
"""
from . import rules

OUTLINE_SCAFFOLD = [
    "开场钩子：一个具体场景或数字，先立住注意力",
    "过程/方法：步骤、对比或清单，信息密度拉满",
    "结尾互动：一个提问，引导评论区",
]

C_OUTLINE_SCAFFOLD = [
    "开场：一个新手常踩的坑或一段真实报错，先立住注意力",
    "核心：概念讲清 + 一段能编译的最小代码，信息密度拉满",
    "结尾：留一个小练习，引导评论区交作业",
]

# C 教学代码示例库：每个主题一段最小可运行代码（gcc -Wall 零警告）。
# output 为程序的标准输出（用于草稿正文与测试断言）。
C_SNIPPETS = {
    "指针": {
        "title": "指针3天搞懂！画图法一次讲清",
        "concept": "指针就一句话：指针就是一个装地址的变量。int *p = &a 的意思是：p 里装的是变量 a 的地址。想改 a 的值，不用碰 a，直接 *p = 10 就行。画图法最管用：画两个格子，一个是 a，一个是 p，箭头从 p 指向 a，*p 就是顺着箭头找到 a。",
        "pitfall": "最常错的是把 *p 和 p 搞混：p 是地址，*p 才是地址指向的值；还有声明时 int *p 的星号是类型的一部分，赋值时 *p 才是取值。",
        "code": ("#include <stdio.h>\n"
                 "int main(void) {\n"
                 "    int a = 5;\n"
                 "    int *p = &a;\n"
                 "    *p = 10;\n"
                 '    printf("%d\\n", a);\n'
                 "    return 0;\n"
                 "}"),
        "output": "10",
    },
    "数组": {
        "title": "数组3天搞懂！下标从0开始记牢",
        "concept": "数组就是一排连续的格子，下标从 0 开始，a[0] 是第一个，a[4] 是第五个。数组名在大多数场合就是首元素的地址，所以数组和指针走得很近，但数组不是指针：数组名不能被赋值。",
        "pitfall": "最常错的是下标越界：5 个元素的数组只有 a[0] 到 a[4]，写 a[5] 就越界了，是未定义行为，编译器不一定报错，但运行结果会错。",
        "code": ("#include <stdio.h>\n"
                 "int main(void) {\n"
                 "    int a[5] = {78, 92, 85, 66, 90};\n"
                 "    int i, sum = 0;\n"
                 "    for (i = 0; i < 5; i++) sum += a[i];\n"
                 '    printf("%d\\n", sum / 5);\n'
                 "    return 0;\n"
                 "}"),
        "output": "82",
    },
    "循环": {
        "title": "循环3天搞懂！for循环一次讲清",
        "concept": "for 循环三要素写在一行：初始化、条件、步进。for (i = 1; i <= 100; i++) 的意思是：i 从 1 开始，每次加 1，加到 100 为止。循环体里放重复做的事，循环变量记得更新，否则就是死循环。",
        "pitfall": "最常错的是条件写反（i <= 100 写成 i >= 100，循环一次都不跑），还有循环体内外分不清：累加的 sum 要定义在循环外面。",
        "code": ("#include <stdio.h>\n"
                 "int main(void) {\n"
                 "    int i, sum = 0;\n"
                 "    for (i = 1; i <= 100; i++) sum += i;\n"
                 '    printf("%d\\n", sum);\n'
                 "    return 0;\n"
                 "}"),
        "output": "5050",
    },
    "函数": {
        "title": "函数3天搞懂！参数返回值一次讲清",
        "concept": "函数就是把一段重复的逻辑包起来：参数是传进去的原料，返回值是做完交出来的结果。int add(int x, int y) 的意思是：收两个 int，返回一个 int。main 里调用 add(3, 4)，就拿到 7。",
        "pitfall": "最常错的是声明和定义对不上（参数个数或类型不一致），还有忘了写返回值：声明了 int 返回值，函数体里却没 return。",
        "code": ("#include <stdio.h>\n"
                 "int add(int x, int y) { return x + y; }\n"
                 "int main(void) {\n"
                 '    printf("%d\\n", add(3, 4));\n'
                 "    return 0;\n"
                 "}"),
        "output": "7",
    },
    "结构体": {
        "title": "结构体3天搞懂！先定义再用",
        "concept": "结构体就是把几个不同类型的数据打包成一个整体：struct Student 里有姓名、成绩。定义在 main 外面，用的时候 struct Student s = {\"张三\", 92}，取值用点号：s.name、s.score。",
        "pitfall": "最常错的是忘了 struct 关键字（C 语言里声明变量要写 struct Student s，不是只写 Student s），还有字符串成员要用字符数组，不能直接赋值整个字符串。",
        "code": ("#include <stdio.h>\n"
                 'struct Student { char name[20]; int score; };\n'
                 "int main(void) {\n"
                 '    struct Student s = {"张三", 92};\n'
                 '    printf("%s %d\\n", s.name, s.score);\n'
                 "    return 0;\n"
                 "}"),
        "output": "张三 92",
    },
    "文件": {
        "title": "文件3天搞懂！fopen配fclose",
        "concept": "文件操作三步：fopen 打开，fgets/fprintf 读写，fclose 关闭。fopen 返回 NULL 说明打不开，一定要先判空再读。读一行用 fgets，写一行用 fprintf，打开和关闭必须成对出现。",
        "pitfall": "最常错的是忘了 fclose（写的内容可能还在缓冲区，没落盘），还有 fopen 失败不判空就直接读，会崩。记住：fopen 和 fclose 成对出现。",
        "code": ("#include <stdio.h>\n"
                 "int main(void) {\n"
                 '    FILE *fp = fopen("students.txt", "r");\n'
                 '    if (fp == NULL) { printf("打不开文件。\\n"); return 1; }\n'
                 "    char line[128];\n"
                 '    if (fgets(line, sizeof line, fp) != NULL) printf("%s", line);\n'
                 "    fclose(fp);\n"
                 "    return 0;\n"
                 "}"),
        "output": "有 students.txt 打印第一行，否则提示打不开文件。",
    },
}

# 默认草稿：实验一第一个 C 程序（hello.c），与 ICT 教学赛实验一同一份代码。
DEFAULT_SNIPPET = {
    "title": "第一个C程序3天跑通！从hello开始",
    "concept": "第一个 C 程序就三件事：#include <stdio.h> 引入输入输出，int main(void) 是程序入口，printf 把话打印到屏幕。编译用 gcc hello.c -o hello，运行 ./hello，看到 Hello, openEuler! 就说明环境通了。",
    "pitfall": "最常错的是 main 写成 void main（应为 int main(void)），还有 printf 的引号、分号漏写，编译报错先看第一行。",
    "code": ("#include <stdio.h>\n"
             "int main(void) {\n"
             '    printf("Hello, openEuler!\\n");\n'
             '    printf("这是我的第一个 C 程序。\\n");\n'
             "    return 0;\n"
             "}"),
    "output": "Hello, openEuler!\n这是我的第一个 C 程序。",
}


def _pick_snippet(topic, keywords):
    for kw in list(keywords or []) + [topic or ""]:
        for key in C_SNIPPETS:
            if key and key in kw:
                return key, C_SNIPPETS[key]
    return "", DEFAULT_SNIPPET


def generate_draft_note(topic, keywords, niche="", tags_db=None):
    """按主题生成一篇笔记草稿。

    C 语言领域：返回 C 教学笔记草稿，内嵌代码 gcc -Wall 零警告
    （code_standalone=True，可直接编译运行）。
    非 C 领域：返回通用模板草稿（标题 + 开场钩子 + 三步行程 +
    结尾互动，须由创作者填入真实内容后发布，不含代码）。
    返回 {"title", "body", "tags", "code", "code_standalone"}。
    草稿须由创作者改写后发布，不直接代发。
    """
    key, snip = _pick_snippet(topic, keywords)
    if key or rules.is_c_domain(niche, " ".join(keywords or []) + (topic or "")):
        tag_topic = key or "C语言入门"
        body = (
            f"{snip['concept']}\n"
            f"最小代码（能编译）：\n```c\n{snip['code']}\n```\n"
            f"运行输出：{snip['output']}\n"
            f"常见错误：{snip['pitfall']}\n"
            f"你卡在哪一步？评论区聊聊 👇\n"
            f"#C语言 #C语言入门 #程序设计 #{tag_topic} #代码学习"
        )
        return {"title": snip["title"], "body": body,
                "tags": ["C语言", "C语言入门", "程序设计", tag_topic, "代码学习"],
                "code": snip["code"], "code_standalone": True}
    # 通用模板草稿（非 C 领域）：脚手架正文，须填入真实内容。
    n = rules.pick_numbers(keywords)
    tag_list = [topic]
    if tags_db and niche in tags_db:
        tag_list += [t for t in tags_db[niche] if t != topic][:2]
    body = (
        f"开场钩子：{topic}最值得去的一个场景或数字，先立住注意力。\n"
        f"行程：分三步写，{topic}的路线、花费和交通，信息密度拉满。\n"
        f"结尾互动：问一句，你们去过{topic}吗？评论区聊聊 👇\n"
        + " ".join("#" + t for t in tag_list)
    )
    return {"title": f"{topic}怎么玩？{n}个地方一次讲清", "body": body,
            "tags": tag_list, "code": "", "code_standalone": False}


def generate_topics(niche, keywords, patterns):
    """取前三个钩子结构（数字钩、时间钩、反问钩），各生成一个选题。
    C 语言领域用专用大纲脚手架（概念 + 最小代码 + 练习）。"""
    scaffold = (C_OUTLINE_SCAFFOLD if rules.is_c_domain(niche, " ".join(keywords or []))
                else OUTLINE_SCAFFOLD)
    topics = []
    for name, _pat, template, tip in rules.STYLE_HOOKS[:3]:
        rewrites = rules.rewrite_with_style(
            keywords, [{"name": name, "template": template, "tip": tip}])
        title = rewrites[0][1] if rewrites else ""
        topics.append({
            "hook": name,
            "title": title,
            "tip": tip,
            "angle": f"{name}：{tip}",
            "outline": list(scaffold),
            "niche": niche,
            "keywords": list(keywords),
        })
    return topics
