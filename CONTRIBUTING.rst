Contributing Guidelines
=======================

Issue tracker
-------------
您可以通过 `issue tracker <https://github.com/chaitin/django-pg-partitioning/issues>`__ 提交改进建议、缺陷报告或功能需求，但 **必须** 遵守以下规范：

* **请勿** 重复提交相似的主题或内容。
* **请勿** 讨论任何与本项目无关的内容。
* 我们非常欢迎您提交程序缺陷报告，但在此之前，请确保您已经完整阅读过相关文档，并已经做了一些必要的调查，确定错误并非您自身造成的。在您编写程序缺陷报告时，
  请详细描述您所出现的问题和复现步骤，并附带详细的信息，以便我们能尽快定位问题。

----

You can submit improvement suggestions, bug reports, or feature requests through the `issue tracker <https://github.com/chaitin/django-pg-partitioning/issues>`_,
but you **MUST** adhere to the following specifications:

* **Do not** submit similar topics or content repeatedly.
* **Do not** discuss any content not related to this project.
* We welcome you to submit a bug report, but before doing so, please make sure that you have read the documentation in its entirety and
  have done some necessary investigations to determine that the error is not yours. When you write a bug report, Please describe in detail
  the problem and recurring steps that you have with detailed information so that we can locate the problem as quickly as possible.

Code guidelines
---------------
* 本项目采用 `语义化版本 2.0.0 <https://semver.org/spec/v2.0.0.html>`_
* 本项目使用了 `flask8` `isort` `black` 等代码静态检查工具。提交的代码 **必须** 通过 `lint` 工具检查。某些特殊情况不符合规范的部分，需要按照检查工具要求的方式具体标记出来。
* 公开的 API **必须** 使用 Type Hint 并编写 Docstrings，其他部分 **建议** 使用并在必要的地方为代码编写注释，增强代码的可读性。
* **必须** 限定非 Development 的外部依赖的模块版本为某一个完全兼容的系列。

相关文档:

| `Google Python Style Guide <https://github.com/google/styleguide/blob/gh-pages/pyguide.md>`_
| `PEP 8 Style Guide for Python Code <https://www.python.org/dev/peps/pep-0008/>`_

----

* This project uses a `Semantic Version 2.0.0 <https://semver.org/spec/v2.0.0.html>`_
* This project uses a code static check tool such as `flask8` `isort` `black`. The submitted code **MUST** be checked by the `lint` tool.
  Some special cases that do not meet the specifications need to be specifically marked in the way required by the inspection tool.
* The public API **MUST** use Type Hint and write Docstrings, other parts **SHOULD** use it and write comments to the code where necessary
  to enhance the readability of code.
* External dependencies published with the project **MUST** at least define a fully compatible version family.

Related documents:

| `Google Python Style Guide <https://github.com/google/styleguide/blob/gh-pages/pyguide.md>`_
| `PEP 8 Style Guide for Python Code <https://www.python.org/dev/peps/pep-0008/>`_
