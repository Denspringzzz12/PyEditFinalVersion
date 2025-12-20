import sys
import os
import hashlib
import re
import keyword
import builtins
import threading
import subprocess
import platform
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from qt_material import apply_stylesheet


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # 1. 首先匹配三引号字符串（最高优先级）
        self.triple_string_format = QTextCharFormat()
        self.triple_string_format.setForeground(QColor("#00AA00"))
        self.triple_single_pattern = QRegularExpression(r"'''[^']*(?:'[^']|'[^'])*'''")
        self.triple_double_pattern = QRegularExpression(r'"""[^"]*(?:"[^"]|"[^"]")*"""')

        # 2. 普通字符串 - 绿色
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#00AA00"))
        self.highlighting_rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

        # 3. 注释 - 灰色（在字符串之后）
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#888888"))
        self.highlighting_rules.append((QRegularExpression(r'#.*'), comment_format))

        # 4. 关键字 - 红色（完整单词匹配）
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#FF6B9D"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = keyword.kwlist
        for word in keywords:
            # 使用单词边界确保完整匹配
            pattern = r'\b' + re.escape(word) + r'\b'
            self.highlighting_rules.append((QRegularExpression(pattern), keyword_format))

        # 5. 内置函数 - 蓝色（完整单词匹配）
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#6B8EFF"))
        builtins_list = [name for name in dir(builtins) if not name.startswith('_')]
        for word in builtins_list:
            pattern = r'\b' + re.escape(word) + r'\b'
            self.highlighting_rules.append((QRegularExpression(pattern), builtin_format))

        # 6. 布尔值和None - 深红色
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#DC143C"))
        for word in ['True', 'False', 'None']:
            pattern = r'\b' + re.escape(word) + r'\b'
            self.highlighting_rules.append((QRegularExpression(pattern), bool_format))

        # 7. 数字 - 橙色
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#FF8C00"))
        self.highlighting_rules.append((QRegularExpression(r'\b\d+\b'), number_format))
        self.highlighting_rules.append((QRegularExpression(r'\b\d+\.\d+\b'), number_format))

        # 8. 函数调用 - 青色（后面有括号的单词）
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#32CD32"))
        self.highlighting_rules.append((QRegularExpression(r'\b\w+(?=\()'), function_format))

        # 9. 类名 - 洋红色（class后面的单词）
        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#FF1493"))
        self.highlighting_rules.append((QRegularExpression(r'(?<=\bclass\s+)\w+'), class_format))

        # 10. 装饰器 - 深橙色
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor("#FF4500"))
        self.highlighting_rules.append((QRegularExpression(r'@\w+'), decorator_format))

        # 11. 模块名（import/from后面） - 紫色
        import_format = QTextCharFormat()
        import_format.setForeground(QColor("#9370DB"))
        # import module_name
        self.highlighting_rules.append((QRegularExpression(r'(?<=\bimport\s+)\w+'), import_format))
        # from module_name
        self.highlighting_rules.append((QRegularExpression(r'(?<=\bfrom\s+)\w+'), import_format))

        # 12. 运算符 - 金色（小心匹配，避免匹配单词中的字符）
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor("#FFD700"))
        # 只匹配作为独立token的运算符
        operator_patterns = [
            r'\+\+', r'--',  # 先匹配 ++ --
            r'\+', r'-', r'\*', r'/', r'%',  # 算术运算符
            r'=', r'==', r'!=', r'<', r'>', r'<=', r'>=',  # 比较运算符
            r'\+=', r'-=', r'\*=', r'/=', r'%=',  # 复合赋值
            r'\.', r',', r':', r';',  # 分隔符
            r'\(', r'\)', r'\[', r'\]', r'\{', r'\}',  # 括号
        ]

        # 逻辑运算符作为独立单词匹配
        logic_operators = [r'\band\b', r'\bor\b', r'\bnot\b', r'\bin\b', r'\bis\b']
        for pattern in logic_operators:
            self.highlighting_rules.append((QRegularExpression(pattern), operator_format))

        # 其他运算符
        for pattern in operator_patterns:
            self.highlighting_rules.append((QRegularExpression(pattern), operator_format))

    def highlightBlock(self, text):
        # 先处理三引号字符串
        triple_single_match = self.triple_single_pattern.match(text)
        while triple_single_match.hasMatch():
            start = triple_single_match.capturedStart()
            length = triple_single_match.capturedLength()
            self.setFormat(start, length, self.triple_string_format)
            triple_single_match = self.triple_single_pattern.match(text, start + length)

        triple_double_match = self.triple_double_pattern.match(text)
        while triple_double_match.hasMatch():
            start = triple_double_match.capturedStart()
            length = triple_double_match.capturedLength()
            self.setFormat(start, length, self.triple_string_format)
            triple_double_match = self.triple_double_pattern.match(text, start + length)

        # 处理其他规则（按优先级）
        for pattern, fmt in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                start = match.capturedStart()
                length = match.capturedLength()

                # 检查这个匹配是否已经在三引号字符串中被格式化了
                already_formatted = False
                for i in range(start, start + length):
                    if self.format(i).foreground().color() == self.triple_string_format.foreground().color():
                        already_formatted = True
                        break

                if not already_formatted:
                    self.setFormat(start, length, fmt)

    def is_in_triple_string(self, text, position):
        triple_single_match = self.triple_single_pattern.match(text)
        while triple_single_match.hasMatch():
            start = triple_single_match.capturedStart()
            end = start + triple_single_match.capturedLength()
            if start <= position < end:
                return True
            triple_single_match = self.triple_single_pattern.match(text, end)

        triple_double_match = self.triple_double_pattern.match(text)
        while triple_double_match.hasMatch():
            start = triple_double_match.capturedStart()
            end = start + triple_double_match.capturedLength()
            if start <= position < end:
                return True
            triple_double_match = self.triple_double_pattern.match(text, end)

        return False


class CodeCompleter:
    def __init__(self):
        self.keywords = set(keyword.kwlist)
        self.builtins = set(dir(builtins))
        self.common_modules = {
            'os', 'sys', 're', 'json', 'time', 'datetime', 'math',
            'random', 'requests', 'numpy', 'pandas', 'matplotlib'
        }
        self.user_definitions = set()

        # 模块成员缓存
        self.module_members = {}

    def get_completions(self, text, prefix):
        if not prefix:
            return []

        completions = []

        # 检查是否在模块访问中 (如 time.sleep)
        if '.' in prefix:
            parts = prefix.split('.')
            if len(parts) == 2:
                module_prefix, member_prefix = parts
                members = self.get_module_members(module_prefix, text)
                completions.extend([f"{module_prefix}.{m}" for m in members if m.startswith(member_prefix)])
                return completions[:15]

        # 普通补全
        completions.extend([kw for kw in self.keywords if kw.lower().startswith(prefix.lower())])
        completions.extend([func for func in self.builtins if func.lower().startswith(prefix.lower())])
        completions.extend([mod for mod in self.common_modules if mod.lower().startswith(prefix.lower())])
        completions.extend([defn for defn in self.user_definitions if defn.lower().startswith(prefix.lower())])

        # 从导入语句中获取模块
        import_pattern = r'import\s+(\w+)|\s+from\s+(\w+)'
        imports = re.findall(import_pattern, text)
        for imp in imports:
            module_name = imp[0] or imp[1]
            if module_name and module_name.lower().startswith(prefix.lower()):
                completions.append(module_name)

        return list(set(completions))[:15]

    def get_module_members(self, module_name, text):
        if module_name in self.module_members:
            return self.module_members[module_name]

        members = []
        try:
            # 检查是否是已导入的模块
            import_pattern = rf'import\s+{module_name}|\s+from\s+{module_name}\s+import'
            if re.search(import_pattern, text):
                try:
                    module = __import__(module_name)
                    members = [attr for attr in dir(module) if not attr.startswith('_')]
                except:
                    pass
        except:
            pass

        # 为常见模块添加默认成员
        if module_name == 'time' and not members:
            members = ['sleep', 'time', 'ctime', 'gmtime', 'localtime', 'mktime', 'strftime', 'strptime']
        elif module_name == 'os' and not members:
            members = ['path', 'listdir', 'mkdir', 'remove', 'rename', 'system']
        elif module_name == 'sys' and not members:
            members = ['argv', 'exit', 'path', 'stdout', 'stderr', 'stdin']

        self.module_members[module_name] = members
        return members

    def update_user_definitions(self, text):
        self.user_definitions.clear()

        func_pattern = r'def\s+(\w+)\s*\('
        functions = re.findall(func_pattern, text)
        self.user_definitions.update(functions)

        class_pattern = r'class\s+(\w+)'
        classes = re.findall(class_pattern, text)
        self.user_definitions.update(classes)

        var_pattern = r'^(\w+)\s*='
        variables = re.findall(var_pattern, text, re.MULTILINE)
        self.user_definitions.update(variables)


class CompletionPopup(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedWidth(300)
        self.setFixedHeight(200)

        # 暗黑主题样式
        self.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #444;
                font-family: Consolas;
                font-size: 11pt;
                color: #e0e0e0;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:selected {
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
        """)

    def showEvent(self, event):
        super().showEvent(event)
        self.clearFocus()

    def focusOutEvent(self, event):
        pass


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFont(QFont("Consolas", 11))
        self.highlighter = PythonSyntaxHighlighter(self.document())

        # 创建补全弹窗
        self.completion_popup = CompletionPopup(self)
        self.completion_popup.itemClicked.connect(self.apply_completion)
        self.completion_popup.hide()

        self.code_completer = CodeCompleter()

        # 连接文本变化信号
        self.textChanged.connect(self.on_text_changed)

        # 设置定时器用于延迟触发补全
        self.completion_timer = QTimer()
        self.completion_timer.setSingleShot(True)
        self.completion_timer.timeout.connect(self.check_for_completions)

        # Tab键处理标志
        self.tab_just_used = False
        # 防止重复缩进标志
        self.colon_just_processed = False

    def on_text_changed(self):
        # 延迟触发补全检查
        self.completion_timer.stop()
        self.completion_timer.start(150)

        # 更新用户定义的内容
        text = self.toPlainText()
        self.code_completer.update_user_definitions(text)

    def check_for_completions(self):
        if not self.hasFocus():
            return

        if self.tab_just_used:
            self.tab_just_used = False
            return

        cursor = self.textCursor()
        text = self.toPlainText()
        pos = cursor.position()

        # 获取当前单词
        line_start = text.rfind('\n', 0, pos) + 1
        current_line = text[line_start:pos]

        # 从当前位置向前找到单词开始
        word_start = 0
        for i in range(len(current_line) - 1, -1, -1):
            ch = current_line[i]
            if not (ch.isalnum() or ch == '_' or ch == '.'):
                word_start = i + 1
                break

        current_word = current_line[word_start:] if word_start < len(current_line) else ""

        if len(current_word) > 0:
            completions = self.code_completer.get_completions(text, current_word)
            if completions:
                self.show_completions(completions, cursor, current_word)
            else:
                self.completion_popup.hide()
        else:
            self.completion_popup.hide()

    def show_completions(self, completions, cursor, current_word):
        self.completion_popup.clear()

        filtered_completions = []
        for item in completions:
            if item.lower().startswith(current_word.lower()):
                filtered_completions.append(item)

        if not filtered_completions:
            self.completion_popup.hide()
            return

        # 排序：用户定义 > 关键字 > 内置 > 模块
        def sort_key(x):
            score = 0
            if x in self.code_completer.user_definitions:
                score += 1000
            if x in self.code_completer.keywords:
                score += 500
            if x in self.code_completer.builtins:
                score += 300
            if '.' in x:  # 模块成员
                score += 200
            return (-score, len(x), x.lower())

        filtered_completions.sort(key=sort_key)

        # 显示建议
        for item in filtered_completions[:10]:
            self.completion_popup.addItem(item)

        if self.completion_popup.count() > 0:
            cursor_rect = self.cursorRect(cursor)
            global_pos = self.mapToGlobal(cursor_rect.bottomLeft())

            screen_rect = QApplication.primaryScreen().availableGeometry()
            popup_right = global_pos.x() + self.completion_popup.width()
            popup_bottom = global_pos.y() + self.completion_popup.height()

            if popup_right > screen_rect.right():
                global_pos.setX(screen_rect.right() - self.completion_popup.width())
            if popup_bottom > screen_rect.bottom():
                global_pos.setY(global_pos.y() - self.completion_popup.height() - cursor_rect.height())

            self.completion_popup.move(global_pos)
            self.completion_popup.show()
            self.completion_popup.setCurrentRow(0)
            self.setFocus()
        else:
            self.completion_popup.hide()

    def apply_completion(self, item):
        if not item:
            return

        completion = item.text()
        cursor = self.textCursor()

        text = self.toPlainText()
        pos = cursor.position()

        line_start = text.rfind('\n', 0, pos) + 1
        current_line = text[line_start:pos]

        # 找到当前单词的开始位置
        word_start = 0
        for i in range(len(current_line) - 1, -1, -1):
            ch = current_line[i]
            if not (ch.isalnum() or ch == '_' or ch == '.'):
                word_start = i + 1
                break

        chars_to_delete = len(current_line) - word_start

        if chars_to_delete > 0:
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, chars_to_delete)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, chars_to_delete)

        cursor.insertText(completion)
        self.setTextCursor(cursor)

        self.completion_popup.hide()
        self.setFocus()
        self.completion_timer.stop()

    def keyPressEvent(self, event):
        # 处理Tab键
        if event.key() == Qt.Key.Key_Tab:
            cursor = self.textCursor()
            text = self.toPlainText()
            pos = cursor.position()

            line_start = text.rfind('\n', 0, pos) + 1
            current_line = text[line_start:pos]

            if current_line.strip() == "":
                cursor.insertText("    ")
                self.tab_just_used = True
                event.accept()
                return

        # 检查补全弹窗
        if self.completion_popup.isVisible():
            if event.key() == Qt.Key.Key_Down:
                current_row = self.completion_popup.currentRow()
                if current_row < self.completion_popup.count() - 1:
                    self.completion_popup.setCurrentRow(current_row + 1)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Up:
                current_row = self.completion_popup.currentRow()
                if current_row > 0:
                    self.completion_popup.setCurrentRow(current_row - 1)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
                current_item = self.completion_popup.currentItem()
                if current_item:
                    self.apply_completion(current_item)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Escape:
                self.completion_popup.hide()
                self.setFocus()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Tab:
                current_item = self.completion_popup.currentItem()
                if current_item:
                    self.apply_completion(current_item)
                    self.tab_just_used = True
                event.accept()
                return

        # 处理冒号自动缩进
        if event.text() == ":" and not self.colon_just_processed:
            cursor = self.textCursor()
            text = self.toPlainText()
            pos = cursor.position()

            # 检查是否在字符串或注释内
            if not self.is_in_string_or_comment(text[:pos]):
                super().keyPressEvent(event)
                # 设置标志防止重复处理
                self.colon_just_processed = True
                QTimer.singleShot(10, self.handle_colon_indent)
                # 清除标志
                QTimer.singleShot(100, lambda: setattr(self, 'colon_just_processed', False))
                return

        # 处理普通按键
        super().keyPressEvent(event)

        if event.text() and (event.text().isalnum() or event.text() == '_' or event.text() == '.'):
            self.completion_timer.stop()
            self.completion_timer.start(150)

    def is_in_string_or_comment(self, text_before):
        """检查当前位置是否在字符串或注释内"""

        # 检查是否在注释内
        if '#' in text_before:
            last_comment = text_before.rfind('#')
            last_newline = text_before.rfind('\n')
            if last_comment > last_newline:
                return True

        # 检查是否在单引号字符串内
        single_quotes = text_before.count("'")
        triple_single = text_before.count("'''")

        # 检查是否在双引号字符串内
        double_quotes = text_before.count('"')
        triple_double = text_before.count('"""')

        # 计算有效引号数（考虑转义和三引号）
        single_quotes -= triple_single * 3
        double_quotes -= triple_double * 3

        # 检查是否在三引号字符串内
        if triple_single % 2 == 1 or triple_double % 2 == 1:
            return True

        # 检查是否在普通字符串内
        if single_quotes % 2 == 1 or double_quotes % 2 == 1:
            # 检查转义字符
            if single_quotes % 2 == 1:
                # 检查最后一个单引号是否被转义
                last_single = text_before.rfind("'")
                if last_single > 0 and text_before[last_single - 1] == '\\':
                    # 检查转义字符是否被转义
                    escape_count = 0
                    i = last_single - 1
                    while i >= 0 and text_before[i] == '\\':
                        escape_count += 1
                        i -= 1
                    if escape_count % 2 == 0:  # 偶数个转义字符，引号有效
                        return True
                    else:  # 奇数个转义字符，引号被转义
                        return False
                else:
                    return True

            if double_quotes % 2 == 1:
                # 检查最后一个双引号是否被转义
                last_double = text_before.rfind('"')
                if last_double > 0 and text_before[last_double - 1] == '\\':
                    escape_count = 0
                    i = last_double - 1
                    while i >= 0 and text_before[i] == '\\':
                        escape_count += 1
                        i -= 1
                    if escape_count % 2 == 0:
                        return True
                    else:
                        return False
                else:
                    return True

        return False

    def handle_colon_indent(self):
        cursor = self.textCursor()
        text = self.toPlainText()
        pos = cursor.position()

        if pos > 0 and text[pos - 1] == ":":
            # 检查当前行是否已经有缩进（避免重复缩进）
            line_start = text.rfind('\n', 0, pos - 1) + 1
            current_line = text[line_start:pos - 1]

            # 检查下一行是否已经有缩进
            next_line_start = pos
            if next_line_start < len(text):
                # 找到下一行的开始
                next_newline = text.find('\n', next_line_start)
                if next_newline == -1:
                    next_newline = len(text)
                next_line = text[next_line_start:next_newline]

                # 如果下一行已经有非空白内容，不添加缩进
                if next_line.strip() != "":
                    return

            indent = ""
            for char in current_line:
                if char in [' ', '\t']:
                    indent += char
                else:
                    break

            indent += "    "

            # 只插入一次新行和缩进
            cursor.insertText(f"\n{indent}")

    def mousePressEvent(self, event):
        if self.completion_popup.isVisible():
            self.completion_popup.hide()
        super().mousePressEvent(event)

    def focusOutEvent(self, event):
        if event.reason() != Qt.FocusReason.PopupFocusReason:
            self.completion_popup.hide()
        super().focusOutEvent(event)


class TerminalManager:
    def __init__(self):
        self.current_directory = self.get_home_directory()

    def get_home_directory(self):
        system = platform.system().lower()
        if system == "windows":
            return os.path.expanduser("~")
        elif system == "darwin":
            return os.path.expanduser("~")
        else:
            return "/data/data/com.example.python/files" if os.path.exists("/data/data") else os.path.expanduser("~")

    def execute_command(self, command):
        try:
            if command.strip() == "clear":
                return "", ""

            if command.startswith("cd "):
                new_dir = command[3:].strip()
                if new_dir == "..":
                    self.current_directory = os.path.dirname(self.current_directory)
                elif os.path.isdir(new_dir):
                    self.current_directory = new_dir
                elif os.path.isdir(os.path.join(self.current_directory, new_dir)):
                    self.current_directory = os.path.join(self.current_directory, new_dir)
                else:
                    return f"cd: {new_dir}: 目录不存在\n", ""
                return f"切换到目录: {self.current_directory}\n", ""

            if command.startswith("pip "):
                return self.execute_pip_command(command)

            if platform.system().lower() == "windows":
                result = subprocess.run(f"cd /d {self.current_directory} && {command}",
                                        shell=True, capture_output=True, text=True, cwd=self.current_directory)
            else:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=self.current_directory)

            return result.stdout, result.stderr

        except Exception as e:
            return "", f"命令执行错误: {str(e)}\n"

    def execute_pip_command(self, command):
        try:
            if platform.system().lower() == "linux" and os.path.exists("/data/data"):
                pip_command = f"python -m {command}"
            else:
                pip_command = command

            result = subprocess.run(pip_command, shell=True, capture_output=True, text=True, cwd=self.current_directory)
            return result.stdout, result.stderr

        except Exception as e:
            return "", f"pip命令执行错误: {str(e)}\n"

    def get_prompt(self):
        system = platform.system().lower()
        if system == "windows":
            return f"{self.current_directory}> "
        else:
            dir_name = os.path.basename(self.current_directory)
            if not dir_name:
                dir_name = "/"
            return f"user@{platform.node()}:{dir_name}$ "


class PyEditIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.current_encoding = "utf-8"
        self.is_running = False
        self.terminal_expanded = False
        self.terminal_manager = TerminalManager()
        self.terminal_history = []
        self.current_platform = self.detect_platform()
        self.init_ui()

    def detect_platform(self):
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "ios" if "iPhone" in platform.platform() else "macos"
        else:
            return "android" if os.path.exists("/data/data") else "linux"

    def init_ui(self):
        self.setWindowTitle(f"PyEdit IDE - {self.current_platform.upper()}")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.create_toolbar()
        self.create_code_editor(main_layout)
        self.create_output_area(main_layout)
        self.create_terminal_area(main_layout)
        self.create_status_bar()

    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        toolbar.addAction("新建", self.open_new_file_dialog)
        toolbar.addAction("打开", self.open_file)
        toolbar.addAction("运行", self.run_code)
        toolbar.addAction("终端", self.toggle_terminal)

    def create_code_editor(self, parent_layout):
        code_group = QGroupBox("代码编辑器")
        code_layout = QVBoxLayout()

        self.code_editor = CodeEditor(self)
        code_layout.addWidget(self.code_editor)

        code_group.setLayout(code_layout)
        parent_layout.addWidget(code_group)

    def create_output_area(self, parent_layout):
        output_group = QGroupBox("输出结果")
        output_layout = QVBoxLayout()

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Consolas", 10))

        output_layout.addWidget(self.output_area)
        output_group.setLayout(output_layout)
        parent_layout.addWidget(output_group)

    def create_terminal_area(self, parent_layout):
        self.terminal_group = QGroupBox("终端")
        terminal_layout = QVBoxLayout()

        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setFont(QFont("Consolas", 10))
        self.terminal_output.setStyleSheet("background-color: black; color: white;")
        self.terminal_output.setText(self.terminal_manager.get_prompt())

        terminal_layout.addWidget(self.terminal_output)

        input_layout = QHBoxLayout()
        self.terminal_input = QLineEdit()
        self.terminal_input.returnPressed.connect(self.execute_terminal_command)
        input_layout.addWidget(self.terminal_input)

        send_btn = QPushButton("发送")
        send_btn.clicked.connect(self.execute_terminal_command)
        input_layout.addWidget(send_btn)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_terminal)
        input_layout.addWidget(clear_btn)

        terminal_layout.addLayout(input_layout)
        self.terminal_group.setLayout(terminal_layout)
        self.terminal_group.setVisible(False)
        parent_layout.addWidget(self.terminal_group)

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            f"平台: {self.current_platform} | 编码: {self.current_encoding} | 文件: {self.current_file or '未打开文件'}")

    def open_new_file_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("新建文件")
        layout = QVBoxLayout()

        filename_input = QLineEdit()
        filename_input.setPlaceholderText("example.py")
        layout.addWidget(filename_input)

        encoding_combo = QComboBox()
        encoding_combo.addItems(["utf-8", "gbk", "utf-16"])
        layout.addWidget(encoding_combo)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        create_btn = QPushButton("创建")
        create_btn.clicked.connect(
            lambda: self.create_new_file(filename_input.text(), encoding_combo.currentText(), dialog))
        btn_layout.addWidget(create_btn)

        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def create_new_file(self, filename, encoding, dialog):
        if not filename:
            QMessageBox.warning(self, "提示", "请输入文件名")
            return

        self.current_file = filename
        self.current_encoding = encoding
        self.code_editor.setPlainText("# 新建文件\nprint('Hello PyEdit!')\n")
        self.output_area.clear()
        dialog.accept()
        self.update_status()

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "打开文件", "", "Python Files (*.py);;All Files (*)")

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                self.current_file = file_path
                self.code_editor.setPlainText(content)
                self.output_area.clear()
                self.update_status()
                QMessageBox.information(self, "提示", f"已打开文件: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开文件失败: {e}")

    def run_code(self):
        if self.is_running:
            QMessageBox.warning(self, "提示", "代码正在执行中，请稍候...")
            return

        code = self.code_editor.toPlainText()
        if not code:
            QMessageBox.warning(self, "提示", "没有代码可执行")
            return

        self.is_running = True
        self.output_area.setText("代码执行中...\n")

        def execute_code():
            try:
                import io
                import sys
                from contextlib import redirect_stdout, redirect_stderr

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()

                compiled_code = compile(code, '<string>', 'exec')
                exec(compiled_code, {})

                output = sys.stdout.getvalue()
                error = sys.stderr.getvalue()

                sys.stdout = old_stdout
                sys.stderr = old_stderr

                result = ""
                if output:
                    result += f"输出:\n{output}\n"
                if error:
                    result += f"错误:\n{error}\n"
                if not output and not error:
                    result = "代码执行完成，无输出"

                QMetaObject.invokeMethod(self, "update_output", Qt.ConnectionType.QueuedConnection, Q_ARG(str, result))

            except SyntaxError as e:
                error_msg = f"语法错误: {e.msg}\n位于第{e.lineno}行，第{e.offset}列"
                QMetaObject.invokeMethod(self, "update_output", Qt.ConnectionType.QueuedConnection,
                                         Q_ARG(str, error_msg))
            except Exception as ex:
                QMetaObject.invokeMethod(self, "update_output", Qt.ConnectionType.QueuedConnection,
                                         Q_ARG(str, f"执行错误: {ex}"))
            finally:
                self.is_running = False

        threading.Thread(target=execute_code, daemon=True).start()

    @pyqtSlot(str)
    def update_output(self, text):
        self.output_area.setText(text)

    def toggle_terminal(self):
        self.terminal_expanded = not self.terminal_expanded
        self.terminal_group.setVisible(self.terminal_expanded)

    def execute_terminal_command(self):
        command = self.terminal_input.text().strip()
        if not command:
            return

        self.terminal_history.append(f"{self.terminal_manager.get_prompt()}{command}")

        def run_command():
            stdout, stderr = self.terminal_manager.execute_command(command)

            output_lines = []
            if stdout:
                output_lines.append(stdout)
            if stderr:
                output_lines.append(stderr)

            output_lines.append(self.terminal_manager.get_prompt())

            output_text = f"{self.terminal_manager.get_prompt()}{command}\n" + "\n".join(output_lines)

            QMetaObject.invokeMethod(self.terminal_output, "append", Qt.ConnectionType.QueuedConnection,
                                     Q_ARG(str, output_text))
            QMetaObject.invokeMethod(self.terminal_input, "clear", Qt.ConnectionType.QueuedConnection)

        threading.Thread(target=run_command, daemon=True).start()

    def clear_terminal(self):
        self.terminal_output.setText(self.terminal_manager.get_prompt())

    def update_status(self):
        self.status_bar.showMessage(
            f"平台: {self.current_platform} | 编码: {self.current_encoding} | 文件: {self.current_file or '未打开文件'}")


def main():
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_teal.xml')

    window = PyEditIDE()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
