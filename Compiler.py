# ========================
# 教学型C语言编译器
# 设计特点：模块化/可扩展/教学友好
# ========================

import os
import pprint
import tkinter as tk

from enum import Enum
from tkinter import ttk
from tkinter.font import Font
from tkinter import scrolledtext

# ----------------------
# 核心数据结构定义
# ----------------------
class TokenType(Enum):
    # 基础类型
    INT = 'INT'          # 整型类型声明
    VOID = 'VOID'        # 无类型声明
    FLOAT = 'FLOAT'      # 浮点类型声明
    STRING = 'STRING'    # 字符串字面量
    NUMBER = 'NUMBER'    # 数字字面量
    IDENTIFIER = 'IDENTIFIER'  # 标识符

    # 运算符
    ASSIGN = '='         # 赋值运算符
    PLUS = '+'           # 加法
    MINUS = '-'          # 减法
    STAR = '*'           # 乘法
    SLASH = '/'          # 除法

    # 比较符
    EQ = '=='            # 等于
    NE = '!='            # 不等于
    LT = '<'             # 小于
    GT = '>'             # 大于
    LE = '<='            # 小于等于
    GE = '>='            # 大于等于

    # 标点
    SEMI = ';'           # 分号
    COMMA = ','          # 逗号
    QUOTE = '"'          # 引号
    LPAREN = '('         # 左括号
    RPAREN = ')'         # 右括号
    LBRACE = '{'         # 左花括号
    RBRACE = '}'         # 右花括号
    AMPERSAND = '&'      # 取地址符

    # 关键字
    IF = 'if'            # 条件语句关键字
    ELSE = 'else'        # else分支关键字
    WHILE = 'while'      # while关键字
    SCANF = 'scanf'      # scanf关键字
    PRINTF = 'printf'    # printf关键字

    # 特殊标记
    EOF = 'EOF'          # 文件结束标记


class Token:
    # 初始化函数
    def __init__(self, type, value, lineno, colno):
        self.type = type      # Token类型（来自TokenType）
        self.value = value    # 原始值（代码中实际书写的字符内容）
        self.lineno = lineno  # 行号定位
        self.colno = colno    # 列号定位

    # 输出调试信息时用
    def __repr__(self):
        return f"<{self.type}  {self.value}  @ {self.lineno}:{self.colno}>"

    def __str__(self):
        return f"'{self.value}'"



# ----------------------
# 错误处理器
# ----------------------
class ErrorHandler:
    def __init__(self):
        self.errors = []  # 错误信息收集器

    # 添加错误信息
    def add_error(self, msg, lineno, colno):
        self.errors.append(f"Line {lineno}:{colno} --- {msg}")

    # 判断是否出错
    def has_errors(self):
        return bool(self.errors)

    # 输出错误信息
    def show_errors(self):
        for err in self.errors:
            print(f"[ERROR] {err}")



# ----------------------
# 表格管理模块
# ----------------------
class Scope:
    """作用域层级封装"""
    def __init__(self, parent=None):
        self.vars = {}          # 当前作用域符号表 {name: (type, addr)}
        self.parent = parent    # 父作用域指针
        # self.next_addr = 0     # 局部地址分配器

    """def add_var(self, name, var_type):
        #在当前作用域添加变量
        if name in self.vars:
            raise ValueError(f"重复定义变量 {name}")
        self.vars[name] = (var_type, self.next_addr)
        self.next_addr += 4  # 保持4字节对齐"""

    def get_var(self, name):
        """从当前作用域向外层逐级查找"""
        scope = self
        while scope:
            if name in scope.vars:
                return scope.vars[name]
            scope = scope.parent
        raise ValueError(f"未定义变量 {name}")


class SymbolTable:
    """符号表管理系统"""
    def __init__(self):
        self.global_funcs = set()  # 全局作用域函数表 (name)
        self.current_scope = Scope()  # 初始化全局作用域
        self.scope_stack = [self.current_scope]  # 作用域栈
        self.global_address = 0  # 全局地址分配器

    def enter_scope(self):
        """进入新作用域"""
        new_scope = Scope(self.current_scope)
        self.current_scope = new_scope
        self.scope_stack.append(new_scope)

    def exit_scope(self):
        """退出当前作用域"""
        if len(self.scope_stack) > 1:  # 保护全局作用域
            self.scope_stack.pop()
            self.current_scope = self.scope_stack[-1]
        else:
            raise ValueError("不可退出全局作用域")

    # 添加变量
    def add_var(self, name, var_type):
        if name in self.current_scope.vars:
            raise ValueError(f"重复定义变量 {name}")
        # 分配全局地址并递增
        addr = self.global_address
        self.current_scope.vars[name] = (var_type, addr)
        self.global_address += 4  # 4字节对齐

    # 查找变量
    def get_var(self, name):
        """代理到当前作用域"""
        return self.current_scope.get_var(name)

    # 添加函数
    def add_function(self, name):
        if name in self.global_funcs:
            raise ValueError(f"重复定义函数 {name}")
        self.global_funcs.add(name)

    # 查找函数
    def get_function(self, name):
        if name not in self.global_funcs:
            raise ValueError(f"未定义函数 {name}")



# ----------------------
# 词法分析器
# ----------------------
class Lexer:
    def __init__(self, text, error_handler):
        self.text = text           # 源代码字符串
        self.pos = 0               # 当前字符位置
        self.lineno = 1            # 当前行号
        self.colno = 1             # 当前列号
        self.error_handler = error_handler  # 绑定错误处理器
        self.current_char = self.text[0] if text else None  # 当前处理字符

    # 内部方法：字符扫描器
    def _advance(self):
        # 处理换行
        if self.current_char == '\n':
            self.lineno += 1
            self.colno = 0

        # 移动扫描指针
        self.pos += 1
        self.colno += 1

        # 更新当前字符
        if self.pos < len(self.text):
            self.current_char = self.text[self.pos]
        else:
            self.current_char = None  # 处理结束

    def _skip_whitespace(self):
        # 跳过所有空白字符
        while self.current_char is not None and self.current_char.isspace():
            self._advance()

    def _read_number(self):
        value = ''                 # 存储数字字符串
        is_float = False           # 记录变量类型
        start_col = self.colno     # 记录起始列号

        # 循环读取数字和小数点
        while self.current_char is not None and (self.current_char.isdigit() or self.current_char == '.'):

            # 遇到小数点时检查是否已存在
            if self.current_char == '.':
                if is_float:  # 若之前已有小数点，则终止扫描,防止出现多个小数点
                    break
                is_float = True
            value += self.current_char  # 读入新字符并存储
            self._advance()

        # 返回对应类型的数值
        return float(value) if is_float else int(value)

    def _read_identifier(self):
        value = ''                 # 存储字符串
        start_col = self.colno     # 记录起始列号

        # 读取字母/数字/下划线组合
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            value += self.current_char
            self._advance()

        # 关键字检测逻辑
        if value == 'if':
            return Token(TokenType.IF, value, self.lineno, start_col)
        elif value == 'else':
            return Token(TokenType.ELSE, value, self.lineno, start_col)
        elif value == 'int':
            return Token(TokenType.INT, value, self.lineno, start_col)
        elif value == 'float':
            return Token(TokenType.FLOAT, value, self.lineno, start_col)
        elif value == 'while':
            return Token(TokenType.WHILE, value, self.lineno, start_col)
        elif value == 'scanf':
            return Token(TokenType.SCANF, value, self.lineno, start_col)
        elif value == 'printf':
            return Token(TokenType.PRINTF, value, self.lineno, start_col)
        elif value == 'void':
            return Token(TokenType.VOID, value, self.lineno, start_col)

        return Token(TokenType.IDENTIFIER, value, self.lineno, start_col)

    def get_next_token(self):
        while self.current_char is not None:
            # 过滤无意义字符
            if self.current_char.isspace():
                self._skip_whitespace()
                continue

            # 处理数字
            if self.current_char.isdigit():
                value = self._read_number()
                return Token(TokenType.NUMBER, value, self.lineno, self.colno - len(str(value)))  # 该数字的列号 = 当前指针所在列号 - 数字字符串长度

            # 处理标识符
            if self.current_char.isalpha() or self.current_char == '_':
                return self._read_identifier()

            # 字符串字面量解析（仅支持"%d"或"%f"）
            if self.current_char == '"':
                col = self.colno  # 记录列号
                self._advance()  # 跳过引号
                s = ""  # 用于保存字符串内容
                while self.current_char is not None and self.current_char != '"':
                    s += self.current_char
                    self._advance()
                self._advance()  # 跳过闭合引号
                return Token(TokenType.STRING, s, self.lineno, col)

            # 处理多字符运算符（==等）
            if self.current_char == '=':
                start_col = self.colno  # 记录起始列
                self._advance()  # 移动指针到下一个字符
                if self.current_char == '=':  # 双等号
                    self._advance()
                    return Token(TokenType.EQ, '==', self.lineno, start_col)
                return Token(TokenType.ASSIGN, '=', self.lineno, start_col)

            if self.current_char == '!':
                self._advance()
                if self.current_char == '=':  # 处理!=
                    self._advance()
                    return Token(TokenType.NE, '!=', self.lineno, self.colno - 2)

            if self.current_char == '<':
                start_col = self.colno  # 记录起始列
                self._advance()  # 移动指针到下一个字符
                if self.current_char == '=':
                    self._advance()
                    return Token(TokenType.LE, '<=', self.lineno, start_col)
                return Token(TokenType.LT, '<', self.lineno, start_col)

            if self.current_char == '>':
                start_col = self.colno  # 记录起始列
                self._advance()  # 移动指针到下一个字符
                if self.current_char == '=':
                    self._advance()
                    return Token(TokenType.GE, '>=', self.lineno, start_col)
                return Token(TokenType.GT, '>', self.lineno, start_col)

            # 处理单字符Token
            for tt in TokenType:  # 遍历所有Token类型
                if self.current_char == tt.value:
                    char = self.current_char  # 保存当前字符
                    col = self.colno  # 保存当前列号
                    self._advance()  # 移动指针到下一个字符
                    return Token(tt, char, self.lineno, col)

            # 错误处理
            self.error_handler.add_error(f"非法字符 '{self.current_char}'", self.lineno, self.colno)
            self._advance()  # 跳过该字符

        # 读取结束
        return Token(TokenType.EOF, None, self.lineno, self.colno)



# ----------------------
# 语法语义分析器 (递归下降)
# ----------------------
class Parser:
    def __init__(self, lexer, error_handler):
        self.lexer = lexer  # 绑定词法分析器
        self.error_handler = error_handler  # 绑定错误处理器
        self.current_token = None  # 当前Token
        self.next_token = None  # 前瞻Token
        self.symbol_table = SymbolTable()  # 创建空符号表

        # 初始化双Token缓冲
        self._advance_tokens()  # 预加载 current_token 和 next_token

    # 推进token
    def _advance_tokens(self):
        """推进Token流，维护 current 和 next 两个指针"""
        self.current_token = self.next_token if self.next_token else self.lexer.get_next_token()  # 更新current_token
        self.next_token = self.lexer.get_next_token()  # 更新next_token

    # 消费token
    def _eat(self, token_type):
        """消费当前Token并推进指针"""
        if self.current_token.type == token_type:  # 判断当前Token类型是否匹配预期
            self._advance_tokens()  # 推进Token流
            return True
        else:  # Token类型不匹配
            self.error_handler.add_error(
                f"期望得到 '{token_type.value}'，实际得到 {self.current_token}",
                self.current_token.lineno,
                self.current_token.colno
            )
            return False

    # 语法分析入口
    def parse(self):
        """启动语法分析流程"""
        return self.program()  # 从program根节点开始解析

    # AST顶层封装
    def program(self):
        """ program : function* """
        functions = []
        while self.current_token.type != TokenType.EOF:  # 直到文件结束
            functions.append(self.function_declaration())  # 处理函数声明
        return ('program', functions)  # 返回AST结构

    # 处理函数声明
    def function_declaration(self):
        """ function_declaration : void IDENTIFIER() { statement_list } """
        self._eat(TokenType.VOID)  # 消费void关键字
        func_name = self.current_token.value  # 保存函数名
        self._eat(TokenType.IDENTIFIER)  # 消费函数名
        self._eat(TokenType.LPAREN)  # 消费左括号
        self._eat(TokenType.RPAREN)  # 消费右括号
        self._eat(TokenType.LBRACE)  # 消费左花括号
        self._enter_scope()  # 进入函数作用域
        statements = []
        while self.current_token.type not in (TokenType.RBRACE, TokenType.EOF):  # 直到文件结束或出现'}'
            stmt = self.statement()  # 递归解析语句块中的语句
            if stmt is not None:  # 过滤因错误恢复机制产生的None节点
                statements.append(stmt)  # 添加AST节点
        self._eat(TokenType.RBRACE)  # 消费右花括号
        self.symbol_table.add_function(func_name)  # 符号表中新增函数记录
        self._exit_scope()  # 退出函数作用域
        return ('function', func_name, statements)  # 返回AST节点

    # 处理语句
    def statement(self):
        """ statement : function_call | declaration | assignment | if_statement | while_statement | scanf_statement | printf_statement | block """
        # 处理函数调用语句与赋值语句
        if self.current_token.type == TokenType.IDENTIFIER:
            # 前瞻判断下一个Token是否为左括号
            if self.next_token.type == TokenType.LPAREN:
                return self.function_call()  # 函数调用语句
            elif self.next_token.type == TokenType.ASSIGN:
                return self.assignment()  # 赋值语句
            else:
                self.error_handler.add_error(
                    f"标识符 '{self.current_token.value}' 位置不合法",
                    self.current_token.lineno,
                    self.current_token.colno
                )
                self._advance_tokens()  # 跳过当前Token，直至出现句首Token
                return

        # 处理其它语句
        elif self.current_token.type in (TokenType.INT, TokenType.FLOAT):
            return self.declaration()  # 变量声明语句
        elif self.current_token.type == TokenType.IF:
            return self.if_statement()  # 条件语句
        elif self.current_token.type == TokenType.WHILE:
            return self.while_statement()  # 循环语句
        elif self.current_token.type == TokenType.SCANF:
            return self.scanf_statement()  # 输入语句
        elif self.current_token.type == TokenType.PRINTF:
            return self.printf_statement()  # 输出语句
        elif self.current_token.type == TokenType.LBRACE:
            return self.block()  # 语句块
        else:
            """# 调试信息，可删除
            self.error_handler.add_error(
                f"当前Token {self.current_token} 非C语言的句首符号，已自动跳过(调试信息)",
                self.current_token.lineno,
                self.current_token.colno
            )"""

            self._advance_tokens()  # 跳过当前Token，直至出现句首Token

    # 处理函数调用语句
    def function_call(self):
        """ function_call : IDENTIFIER(); """
        # 语法分析：检查函数调用语句格式
        func_name = self.current_token.value  # 保存函数名
        lineno = self.current_token.lineno  # 保存函数行号信息
        colno = self.current_token.colno  # 保存函数列号信息
        self._eat(TokenType.IDENTIFIER)  # 消费函数名
        self._eat(TokenType.LPAREN)  # 消费左括号
        self._eat(TokenType.RPAREN)  # 消费右括号
        self._eat(TokenType.SEMI)  # 消费分号

        # 语义分析：检查函数是否声明
        try:
            self.symbol_table.get_function(func_name)
        except ValueError as e:
            self.error_handler.add_error(f"函数 {func_name} 未声明", lineno, colno)

        # 返回AST节点
        return ('function_call', func_name)

    # 处理声明语句
    def declaration(self):
        """ declaration : type IDENTIFIER [= expression] ; """
        # 语法分析：检查声明语句格式
        var_type = self.current_token.value  # 保存类型关键字值（int/float）
        self._eat(self.current_token.type)  # 消费type
        var_lineno = self.current_token.lineno  # 保存变量行号
        var_colno = self.current_token.colno  # 保存变量列号
        var_name = self.current_token.value  # 保存变量名
        self._eat(TokenType.IDENTIFIER)  # 消费标识符
        expr = None
        if self.current_token.type == TokenType.ASSIGN:
            self._eat(TokenType.ASSIGN)  # 消费赋值号
            if self.current_token.type == TokenType.SEMI:
                self.error_handler.add_error("变量声明语句缺少表达式", var_lineno, var_colno)
                self._eat(TokenType.SEMI)  # 消费分号
                return
            expr = self.expression(var_type)  # 递归解析表达式
            self._eat(TokenType.SEMI)  # 消费分号

        # 语义分析：检查变量是否重复定义
        addr = None  # 初始化addr
        try:
            self.symbol_table.add_var(var_name, var_type)  # 符号表注册
            _, addr = self.symbol_table.get_var(var_name)  # 获取变量地址
        except ValueError as e:
            self.error_handler.add_error(f"重复定义变量 '{var_name}'", var_lineno, var_colno)
            addr = -1  # 设置无效地址

        # 返回AST节点
        return ('declaration', var_type, var_name, expr, addr)

    # 处理赋值语句
    def assignment(self):
        """ assignment : IDENTIFIER = expression; """
        # 语法分析：检查赋值语句格式
        var_lineno = self.current_token.lineno  # 保存变量行号
        var_colno = self.current_token.colno  # 保存变量列号
        var_name = self.current_token.value  # 保存变量名
        self._eat(TokenType.IDENTIFIER)  # 消费变量名

        # 语义分析：检查变量是否已声明
        try:
            var_type, addr = self.symbol_table.get_var(var_name)
        except ValueError as e:  # 变量未定义
            self.error_handler.add_error(
                f"赋值前未声明变量 '{var_name}'",
                var_lineno,
                var_colno
            )
            return

        # 语法分析：检查赋值语句格式
        self._eat(TokenType.ASSIGN)  # 消费赋值号
        if self.current_token.type == TokenType.SEMI:
            self.error_handler.add_error("赋值语句缺少表达式", var_lineno, var_colno)
            self._eat(TokenType.SEMI)  # 消费分号
            return

        expr = self.expression(var_type)  # 解析右侧表达式，传递变量类型（用于浮点类型提升）
        self._eat(TokenType.SEMI)  # 消费分号

        # 返回AST节点
        return ('assignment', var_name, expr, addr)

    # 处理分支语句
    def if_statement(self):
        """ if_statement : IF '(' condition ')' statement_list [ ELSE statement_list ]"""
        self._eat(TokenType.IF)  # 消费if关键字
        self._eat(TokenType.LPAREN)  # 消费左括号
        cond = self.condition()  # 解析条件表达式
        self._eat(TokenType.RPAREN)  # 消费右括号

        # 解析then分支
        if self.current_token.type == TokenType.LBRACE:
            then_block = self.block()  # 解析then语句块
        else:
            then_block = self.statement()  # 解析then单语句
        else_block = None

        # 处理else分支
        if self.current_token.type == TokenType.ELSE:
            self._eat(TokenType.ELSE)  # 消费else关键字
            if self.current_token.type == TokenType.LBRACE:
                else_block = self.block()  # 解析else语句块
            else:
                else_block = self.statement()  # 解析else单语句
        return ('if_else', cond, then_block, else_block) if else_block else ('if', cond, then_block)

    # 处理循环语句
    def while_statement(self):
        """ while_statement : WHILE '(' condition ')' statement_list """
        self._eat(TokenType.WHILE)  # 消费while关键字
        self._eat(TokenType.LPAREN)  # 消费左括号
        cond = self.condition()  # 解析条件表达式
        self._eat(TokenType.RPAREN)  # 消费右括号

        # 解析循环体
        if self.current_token.type == TokenType.LBRACE:
            body = self.block()  # 解析块语句
        else:
            body = self.statement()  # 解析单条语句

        return ('while', cond, body)  # 返回AST节点

    # 处理输入语句
    def scanf_statement(self):
        """ scanf_statement : SCANF ( "format", & var ); """
        self._eat(TokenType.SCANF)  # 消费scanf关键字
        self._eat(TokenType.LPAREN)  # 消费左括号
        fmt_string = self.current_token.value  # 保存格式字符串
        self._eat(TokenType.STRING)  # 消费字符串
        self._eat(TokenType.COMMA)  # 消费逗号

        # 语义分析：检查是否错将scanf语句格式错写为printf语句格式
        if self.current_token.type == TokenType.IDENTIFIER:
            self.error_handler.add_error(
                f"'scanf' 语句需要在变量前添加取地址符 '&' ，您是否意味着 'printf' ?",
                self.current_token.lineno,
                self.current_token.colno
            )
            return

        self._eat(TokenType.AMPERSAND)  # 消费取地址符
        var_name = self.current_token.value  # 保存变量名

        # 语义分析：检查使用变量前是否声明
        try:
            var_type, var_addr = self.symbol_table.get_var(var_name)  # 获取变量类型与地址
        except ValueError as e:  # 变量未定义
            self.error_handler.add_error(
                f"在 scanf 语句中，变量 '{var_name}' 使用前未声明",
                self.current_token.lineno,
                self.current_token.colno
            )
            return

        # 语义分析：检查输出变量是否与格式字符串匹配
        if fmt_string == "%d" and var_type != "int":
            self.error_handler.add_error(
                f"%d 期望得到 int 型变量，而变量 '{var_name}' 为 {var_type} 型变量",
                self.current_token.lineno,
                self.current_token.colno
            )
            return
        elif fmt_string == "%f" and var_type != "float":
            self.error_handler.add_error(
                f"%f 期望得到 float 型变量，而变量 '{var_name}' 为 {var_type} 型变量",
                self.current_token.lineno,
                self.current_token.colno
            )
            return

        self._eat(TokenType.IDENTIFIER)  # 消费标识符
        self._eat(TokenType.RPAREN)  # 消费右括号
        self._eat(TokenType.SEMI)  # 消费分号
        return ('scanf', fmt_string, var_name, var_type, var_addr)

    # 处理输出语句
    def printf_statement(self):
        """ printf_statement : PRINTF ( "format", & var); """
        self._eat(TokenType.PRINTF)  # 消费printf关键字
        self._eat(TokenType.LPAREN)  # 消费左括号
        fmt_string = self.current_token.value  # 保存格式字符串
        self._eat(TokenType.STRING)  # 消费字符串
        self._eat(TokenType.COMMA)  # 消费逗号

        # 语义分析：检查是否错将printf语句格式错写为scanf语句格式
        if self.current_token.type == TokenType.AMPERSAND:
            self.error_handler.add_error(
                f"'printf' 语句无需取地址符 '&' ，您是否意味着 'scanf' ?",
                self.current_token.lineno,
                self.current_token.colno
            )
            return

        var_name = self.current_token.value  # 保存变量名
        self._eat(TokenType.IDENTIFIER)  # 消费标识符

        # 语义分析：检查使用变量前是否声明
        try:
            var_type, var_addr = self.symbol_table.get_var(var_name)  # 获取变量类型与地址
        except ValueError as e:  # 变量未定义
            self.error_handler.add_error(
                f"在 printf 语句中，变量 '{var_name}' 使用前未声明",
                self.current_token.lineno,
                self.current_token.colno
            )
            return

        # 语义分析：检查输出变量是否与格式字符串匹配
        if fmt_string == "%d" and var_type != "int":
            self.error_handler.add_error(
                f"%d 期望得到 int 型变量，而变量 '{var_name}' 为 {var_type} 型变量",
                self.current_token.lineno,
                self.current_token.colno
            )
            return
        elif fmt_string == "%f" and var_type != "float":
            self.error_handler.add_error(
                f"%f 期望得到 float 型变量，而变量 '{var_name}' 为 {var_type} 型变量",
                self.current_token.lineno,
                self.current_token.colno
            )
            return

        self._eat(TokenType.RPAREN)  # 消费右括号
        self._eat(TokenType.SEMI)  # 消费分号
        return ('printf', fmt_string, var_name, var_type, var_addr)

    # 处理语句块
    def block(self):
        """ block : LBRACE statement_list RBRACE """
        self._eat(TokenType.LBRACE)  # 消费'{'
        self._enter_scope()  # 进入新作用域
        statements = []  # 用于存储语句块内的语句
        while self.current_token.type not in (TokenType.RBRACE, TokenType.EOF):  # 直到文件结束或出现'}'
            stmt = self.statement()  # 递归解析语句块中的语句
            if stmt is not None:  # 过滤因错误恢复机制产生的None节点
                statements.append(stmt)  # 添加AST节点
        self._eat(TokenType.RBRACE)  # 消费'}'
        self._exit_scope()  # 退出当前作用域
        return ('block', statements)

    # 处理条件语句
    def condition(self):
        """ condition : expression (GT | GE | LT | LE | EQ | NE) expression """

        left = self.expression()  # 左表达式
        op = self.current_token  # 比较运算符

        # 语义分析：检查比较运算符是否合法
        if op.value not in { '==', '!=', '<', '>', '<=', '>=',}:
            self.error_handler.add_error(f"不支持的比较运算符 {op}", self.current_token.lineno, self.current_token.colno)

        self._eat(op.type)  # 消费运算符
        right = self.expression()  # 右表达式

        return (op.value, left, right)  # 返回AST节点

    # 处理表达式语句
    def expression(self, expected_type=None):
        """ expression : term { ('+'|'-') term}* """
        node = self.term(expected_type)  # 先解析term（乘除优先级更高）
        while self.current_token.type in (TokenType.PLUS, TokenType.MINUS):
            op = self.current_token  # 保存运算符
            self._eat(op.type)  # 消费运算符
            node = (op.value, expected_type, node, self.term(expected_type))  # 构建左结合AST
        return node

    # 处理项
    def term(self, expected_type=None):
        """ term : factor {('*' | '/') factor}* """
        node = self.factor(expected_type)  # 解析基础因子
        while self.current_token.type in (TokenType.STAR, TokenType.SLASH):
            op = self.current_token  # 保存操作符(*/)
            self._eat(op.type)  # 消耗操作符
            node = (op.value, expected_type, node, self.factor(expected_type))  # 递归构建AST
        return node

    # 处理因子
    def factor(self, expected_type=None):
        """ factor : NUMBER | IDENTIFIER | LPAREN expression RPAREN | (MINUS factor) """
        token = self.current_token  # 保存当前Token对象
        # 处理一元负号（优先级最高）
        if token.type == TokenType.MINUS:
            self._eat(TokenType.MINUS)
            factor_node = self.factor(expected_type)  # 递归解析右侧因子
            return ('unary_op', '-', expected_type, factor_node)  # 返回一元操作AST节点
        # 处理常数
        elif token.type == TokenType.NUMBER:
            self._eat(TokenType.NUMBER)
            rt_expected_type = expected_type if expected_type else \
                ('float' if isinstance(token.value, float) else 'int')
            return ('const', rt_expected_type, token.value)
        # 处理标识符
        elif token.type == TokenType.IDENTIFIER:
            var_name = self.current_token.value  # 获取变量名
            self._eat(TokenType.IDENTIFIER)  # 消费标识符
            # 语义分析：检查使用变量前是否声明
            try:
                var_type, var_addr = self.symbol_table.get_var(var_name)  # 获取变量类型与地址
            except ValueError as e:  # 变量未定义
                self.error_handler.add_error(
                    f"在表达式中，变量 '{var_name}' 使用前未声明",
                    self.current_token.lineno,
                    self.current_token.colno
                )
                return
            return ('var', var_type, token.value, var_addr)
        # 处理括号表达式
        elif token.type == TokenType.LPAREN:
            self._eat(TokenType.LPAREN)
            node = self.expression(expected_type)  # 递归解析内部表达式
            self._eat(TokenType.RPAREN)
            return node
        else:
            self.error_handler.add_error(f"不合法的表达式", self.current_token.lineno, self.current_token.colno)

    # 作用域代理方法
    def _enter_scope(self):
        self.symbol_table.enter_scope()

    def _exit_scope(self):
        self.symbol_table.exit_scope()



# ----------------------
# 代码生成器（生成栈式汇编）
# ----------------------
class CodeGenerator:
    def __init__(self, symbol_table):
        self.code = []  # 生成的指令列表
        self.label_count = 0  # 标签生成计数器

    # 标签生成器
    def new_label(self):
        self.label_count += 1  # 保证标签唯一
        return f"L{self.label_count}"

    # 代码生成入口
    def generate(self, ast):
        self.code += ["CALL   FUNC_main", "HALT"]  # 程序入口
        for func in ast[1]:  # ast结构为 ('program', [funcs])
            self.gen_function(func)
        return self.code

    # 处理函数声明
    def gen_function(self, node):
        _, name, body = node
        self.code.append(f"LABEL  FUNC_{name}")  # 添加函数入口标签

        for stmt in body:
            self.gen_node(stmt)  # 处理函数体内部语句

        self.code.append("RET")  # 函数返回


    # 节点分发器
    def gen_node(self, node):
        """根据AST节点类型选择处理方法"""

        # 处理函数调用
        if node[0] == 'function_call':
            self.code.append(f"CALL   FUNC_{node[1]}")

        # 处理变量声明
        elif node[0] == 'declaration':
            _, var_type, var_name, expr, addr = node
            # 有初始化表达式
            if expr is not None:
                self.gen_expr(expr)  # 生成表达式计算代码
                if var_type == 'int' and expr[1] == 'float':  # 将浮点数赋值给整型变量
                    self.code.append("INT")  # 截断转换
                elif var_type == 'float' and expr[1] == 'int': # 将整型数赋值给浮点变量
                    self.code.append("FLOAT")  # 提升转换
            # 无初始化表达式
            else:
                default = 0 if var_type == 'int' else 0.0  # 根据变量类型选择默认值
                self.code.append(f"PUSH   #{default}")  # 加载默认值到栈顶
            self.code.append(f"STORE  [{addr}]")  # 存储到变量地址

        # 处理赋值语句
        elif node[0] == 'assignment':
            _, var_name, expr, addr = node
            self.gen_expr(expr)
            self.code.append(f"STORE  [{addr}]")  # 存储到变量地址

        # 处理if语句
        elif node[0] == 'if':
            _, cond, then_block = node
            true_label = self.new_label()
            false_label = self.new_label()
            self.gen_condition(cond, true_label, false_label)
            self.code.append(f"LABEL  {true_label}")
            self.gen_node(then_block)
            self.code.append(f"LABEL  {false_label}")

        # 处理if-else语句
        elif node[0] == 'if_else':
            _, cond, then_block, else_block = node
            true_label = self.new_label()  # then块入口
            false_label = self.new_label()  # else块入口
            end_label = self.new_label()  # 结束标签

            # 生成条件判断逻辑
            self.gen_condition(cond, true_label, false_label)

            # 生成then块代码
            self.code.append(f"LABEL  {true_label}")
            self.gen_node(then_block)
            self.code.append(f"JMP    {end_label}")  # 跳过else块

            # 生成else块代码
            self.code.append(f"LABEL  {false_label}")
            self.gen_node(else_block)

            # 结束标签
            self.code.append(f"LABEL  {end_label}")

        # 处理while语句
        elif node[0] == 'while':
            _, cond, body = node
            loop_start = self.new_label()  # 循环开始标签（条件检查）
            loop_body = self.new_label()  # 循环体入口标签
            loop_end = self.new_label()  # 循环结束标签

            # 条件检查入口
            self.code.append(f"LABEL  {loop_start}")

            # 生成条件判断逻辑
            self.gen_condition(cond, loop_body, loop_end)  # 条件为真进入循环

            # 生成循环体代码
            self.code.append(f"LABEL  {loop_body}")
            self.gen_node(body)  # 递归生成循环语句块代码
            self.code.append(f"JMP    {loop_start}")  # 跳回条件检查

            # 循环结束标签
            self.code.append(f"LABEL  {loop_end}")

        # 处理scanf语句
        elif node[0] == 'scanf':
            _, fmt, var_name, var_type, var_addr = node  # 获取AST子节点
            if fmt == "%d":
                self.code.append(f"IN     INT")  # 读取整型数输入
                self.code.append(f"STORE  [{var_addr}]")  # 存储到变量地址
            elif fmt == "%f":
                self.code.append(f"IN     FLOAT")  # 读取浮点数输入
                self.code.append(f"STORE  [{var_addr}]")  # 存储到变量地址

        # 处理printf语句
        elif node[0] == 'printf':
            _, fmt, var_name, var_type, var_addr = node  # 获取AST子节点
            if fmt == "%d":
                self.code.append(f"LOAD   [{var_addr}]")  # 加载变量
                self.code.append("OUT    INT")  # 输出整数
            elif fmt == "%f":
                self.code.append(f"LOADF  [{var_addr}]")  # 加载变量
                self.code.append("OUT    FLOAT")  # 输出浮点数

        # 处理语句块
        elif node[0] == 'block':
            for node in node[1]:
                self.gen_node(node)  # 递归生成块内所有语句


    # 条件转移处理核心
    def gen_condition(self, cond, true_label, false_label):
        if isinstance(cond, tuple):
            # 提取运算符和子表达式
            op = cond[0]
            left_expr = cond[1]
            right_expr = cond[2]

            # 生成左右表达式的值
            self.gen_expr(left_expr)
            self.gen_expr(right_expr)

            # 比较栈顶的两个值
            self.code.append("CMP")

            # 生成条件跳转指令
            self.code.append(f"{self._jump_map(op)}    {true_label}")
            self.code.append(f"JMP    {false_label}")
        else:
            # 处理布尔值直接判断
            self.gen_expr(cond)
            self.code.append(f"JNZ    {true_label}")
            self.code.append(f"JMP    {false_label}")


    # 表达式处理核心
    def gen_expr(self, expr):
        if expr[0] == 'const':  # 常数
            _, const_type, value = expr
            self.code.append(f"PUSH   #{value}")  # 立即数加载
        elif expr[0] == 'var':  # 变量
            _, var_type, var_name, addr = expr
            op = "LOADF" if var_type == 'float' else "LOAD "  # 根据变量类型选择汇编指令
            self.code.append(f"{op}  [{addr}]")  # 变量加载
        elif expr[0] == 'unary_op':  # 一元负号表达式
            _, op, expr_type, operand = expr
            self.code.append("PUSH   #0")  # 加载常量0
            self.gen_expr(operand)  # 生成操作数代码
            self.code.append("SUB")  # -operand = 0 - operand
        elif isinstance(expr, tuple) and len(expr) == 4:  # 二元运算
            op, expr_type, left, right = expr
            self.gen_expr(left)  # 递归生成左子树代码
            self.gen_expr(right)  # 递归生成右子树代码
            if expr_type == 'float':
                self.code.append(self._f_op_map(op))  # 添加浮点运算指令
            else:
                self.code.append(self._op_map(op))  # 添加整型运算指令

    def _jump_map(self, op):
        """比较运算符 到 跳转指令 的映射"""
        return {
            '==': 'JE ',
            '!=': 'JNE',
            '<' : 'JL ',
            '>' : 'JG ',
            '<=': 'JLE',
            '>=': 'JGE',
        }[op]

    def _op_map(self, op):
        """算术运算符 到 整型运算指令 的映射"""
        return {
            '+': 'ADD',
            '-': 'SUB',
            '*': 'MUL',
            '/': 'DIV'
        }[op]

    def _f_op_map(self, op):
        """算术运算符 到 浮点运算指令 的映射"""
        return {
            '+': 'FADD',
            '-': 'FSUB',
            '*': 'FMUL',
            '/': 'FDIV'
        }[op]



# ----------------------
# 栈式虚拟机（执行汇编代码）
# ----------------------
class StackVM:
    def __init__(self):
        self.memory = {}           # 内存地址空间（模拟RAM） {addr: value}
        self.stack = []            # 运算数据栈（存储数据运算的中间结果）
        self.pc = 0                # 程序计数器（指向当前执行指令的位置）
        self.code = []             # 指令存储器（存储去除标签后的汇编代码）
        self.label_map = {}        # 标签映射表（维护标签名到指令位置的映射）
        self.call_stack = []       # 函数调用栈（保存返回地址）
        self.input_buffer = []     # 输入缓冲区（暂存用户的多次输入）
        self.output_buffer = []    # 输出缓冲区（暂存虚拟机的多次输出）
        self.comparison_flag = 0   # 比较标志位（次栈顶大于栈顶时为1）
        self.waiting_for_input = False  # 输出等待标志位（标记是否在等待输入）

    # 加载并预处理汇编代码
    def load_code(self, asm_code):
        self.code = []  # 去除标签后的汇编代码
        for line in asm_code:
            if line.startswith("LABEL"):
                label = line.split()[1]  # 提取标签名
                self.label_map[label] = len(self.code)  # 记录标签所在指令位置
            else:
                self.code.append(line)

    # 核心执行循环
    def run(self):
        self.output_buffer = []  # 清空缓冲区
        while self.pc < len(self.code):
            instruction = self.code[self.pc]  # 获取当前指令
            self.pc += 1  # 默认顺序执行

            # 解析指令
            parts = instruction.split()  # 分解指令（操作码 + 操作数）
            op = parts[0]  # 提取操作码

            # 指令派发

            # 压栈指令
            if op == "PUSH":
                value_str = parts[1].strip('#')
                if '.' in value_str:
                    value = float(value_str)  # 浮点数
                else:
                    value = int(value_str)  # 整数
                self.stack.append(value)  # 压入运算栈
            # 弹栈指令
            elif op == "POP":
                self.stack.pop()  # 移除栈顶元素

            # 取数指令:加载内存数据到栈顶
            elif op == "LOAD":
                addr = int(parts[1].strip('[]'))  # 获取变量地址（地址格式为[addr]）
                self.stack.append(self.memory.get(addr, 0))  # 若addr不存在，返回默认值0
            # 存数指令：将栈顶值存入内存
            elif op == "STORE":
                addr = int(parts[1].strip('[]'))
                self.memory[addr] = self.stack.pop()
            # 取浮点数指令:加载内存浮点数据到栈顶
            elif op == "LOADF":
                addr = int(parts[1].strip('[]'))  # 获取变量地址
                self.stack.append(self.memory.get(addr, 0.0))  # 若addr不存在，返回默认值0.0

            # 输入指令
            elif op == "IN":
                self.waiting_for_input = True
                gui.status_var.set(" 等待输入...")  # 修改状态栏
                try:
                    fmt = parts[1]  # 获取输入变量类型
                    value_str = gui.get_input_from_textbox()  # 从GUI获取用户输入

                    # 处理取消或关闭窗口的情况
                    if value_str is None:
                        value_str = "0"

                    # 转换输入值
                    try:
                        if fmt == "INT":
                            value = int(value_str)
                        elif fmt == "FLOAT":
                            value = float(value_str)
                        else:
                            raise ValueError(f"不合法的输入格式: {fmt}")
                        self.stack.append(value)  # 将数值存入栈顶
                        gui.status_var.set(" 输入完成")  # 修改状态栏
                    except ValueError:
                        self.stack.append(0)  # 输入无效时使用默认值
                        gui.show_error(f"[Error] 无效输入 '{value_str}'，已使用默认值0")
                except Exception as e:
                    self.stack.append(0)
                    gui.show_error(f"[Error] 输入错误: {str(e)}")
                finally:
                    self.waiting_for_input = False

            # 输出指令
            elif op == "OUT":
                fmt = parts[1]  # 获取输出变量类型
                value = self.stack.pop()  # 弹出栈顶

                if fmt == "INT":
                    output = str(int(value))  # 以整型数格式输出栈顶值
                elif fmt == "FLOAT":
                    output = str(float(value))  # 以浮点数格式输出栈顶值
                else:
                    output = str(value)

                self.output_buffer.append(output)
                self.update_gui_output(output)

                # 命令行输出
                # if fmt == "INT":
                #     print(int(value), end = '\n')  # 以整型数格式输出栈顶值
                # elif fmt == "FLOAT":
                #     print(float(value), end = '\n')  # 以浮点数格式输出栈顶值
                # else:
                #     print(value, end = '\n')  # 为使输出方便观察，此处添加换行，原为 " end = '' "

            # 加法指令
            elif op == "ADD":
                b = self.stack.pop()  # 弹出栈顶
                a = self.stack.pop()  # 弹出次栈顶
                self.stack.append(a + b)  # 压入求和结果
            # 减法指令
            elif op == "SUB":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a - b)
            # 乘法指令
            elif op == "MUL":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a * b)
            # 除法指令
            elif op == "DIV":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a // b)

            # 浮点加法指令
            elif op == "FADD":
                b = self.stack.pop()  # 弹出栈顶
                a = self.stack.pop()  # 弹出次栈顶
                self.stack.append(float(a) + float(b))  # 压入求和结果
            # 浮点减法指令
            elif op == "FSUB":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(float(a) - float(b))
            # 浮点乘法指令
            elif op == "FMUL":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(float(a) * float(b))
            # 浮点除法指令
            elif op == "FDIV":
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(float(a) / float(b))

            # 整型类型转换指令
            elif op == "INT":
                value = self.stack.pop()
                self.stack.append(int(value))
            # 浮点类型转换指令
            elif op == "FLOAT":
                value = self.stack.pop()
                self.stack.append(float(value))

            # 比较指令
            elif op == "CMP":
                b = self.stack.pop()  # 取栈顶
                a = self.stack.pop()  # 取次栈顶
                self.comparison_flag = 1 if a > b else (-1 if a < b else 0)  # 设置比较标志位

            # 无条件跳转指令
            elif op == "JMP":
                self.pc = self.label_map[parts[1]]  # 直接修改指令指针
            # 小于跳转
            elif op == "JL":
                if self.comparison_flag == -1:
                    self.pc = self.label_map[parts[1]]
            # 大于跳转
            elif op == "JG":
                if self.comparison_flag == 1:
                    self.pc = self.label_map[parts[1]]
            # 小于等于跳转
            elif op == "JLE":
                if self.comparison_flag == -1 or self.comparison_flag == 0:
                    self.pc = self.label_map[parts[1]]
            # 大于等于跳转
            elif op == "JGE":
                if self.comparison_flag == 1 or self.comparison_flag == 0:
                    self.pc = self.label_map[parts[1]]
            # 等于跳转
            elif op == "JE":
                if self.comparison_flag == 0:
                    self.pc = self.label_map[parts[1]]
            # 不等跳转
            elif op == "JNE":
                if self.comparison_flag != 0:
                    self.pc = self.label_map[parts[1]]

            # 函数调用指令
            elif op == "CALL":
                self.call_stack.append(self.pc)  # 保存返回地址
                self.pc = self.label_map[parts[1]]  # 修改程序计数器PC
            # 函数返回指令
            elif op == "RET":
                self.pc = self.call_stack.pop()  # 恢复程序计数器PC
            # 停机指令
            elif op == "HALT":
                break  # 停止虚拟机运行

            # 调试用
            else:
                print(f"不支持的汇编指令 '{op}'")


    def update_gui_output(self, text):
        """确保线程安全地更新GUI输出"""
        if hasattr(self, 'gui') and self.gui:
            self.gui.window.after(0, lambda: self.gui.append_output(text))



# ----------------------
# 编译器主流程
# ----------------------
def compile_source(source):
    error_handler = ErrorHandler()  # 初始化错误处理器

    try:
        lexer = Lexer(source, error_handler)  # 词法分析
        parser = Parser(lexer, error_handler)  # 语法分析
        ast = parser.parse()  # 生成AST

        # 调试代码
        # print("AST结构：")
        # import pprint
        # pprint.pprint(ast)

        # 控制台错误检查及打印输出
        # if error_handler.has_errors():
        #     error_handler.show_errors()

        # 错误检查
        if error_handler.has_errors():
            error_msgs = "\n".join(error_handler.errors)
            return None, None, error_msgs

        generator = CodeGenerator(parser.symbol_table)  # 绑定符号表
        asm_code = generator.generate(ast)  # 生成目标代码

        # 虚拟机执行
        vm = StackVM()
        vm.gui = gui  # 关联VM和GUI
        vm.load_code(asm_code)
        # print("汇编代码:")
        # print("\n".join(asm_code))
        vm.run()

        return "\n".join(asm_code), ast, None  # 返回(汇编代码, AST, 错误信息)

    except Exception as e:
        return None, None, str(e)  # 返回错误信息



# ---------------------------
# 用户界面模块
# ---------------------------
class CompilerGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title(" 教学型C语言编译器 v8.6")
        self.vm = None  # 用于持有VM实例

        # 设置窗口尺寸和居中显示
        window_width = 1000
        window_height = 700
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 设置字体
        self.large_font = Font(family="微软雅黑", size=12)
        self.title_font = Font(family="微软雅黑", size=14, weight="bold")
        self.button_font = Font(family="微软雅黑", size=12)
        self.code_font = Font(family="Consolas", size=12)

        self.window.option_add("*Font", self.large_font)  # 设置默认字体

        self.setup_ui()
        self.asm_code = None
        self.ast = None
        self.last_filename = ""
        self.vm_output = ""
        self.input_window = None  # 用于跟踪输入窗口

    def setup_ui(self):
        # 控制区框架（左侧）
        control_frame = tk.Frame(self.window, width=250, padx=20, pady=20)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        # 标题
        title_label = tk.Label(control_frame, text="C语言编译器", font=self.title_font)
        title_label.pack(pady=(0, 20))

        # 输入组件
        tk.Label(control_frame, text="源代码文件名:", font=self.large_font).pack(anchor='w', pady=(0, 5))
        self.filename_entry = tk.Entry(control_frame, width=20, font=self.large_font)
        self.filename_entry.pack(fill=tk.X, pady=(0, 20))

        # 按钮组
        btn_config = {
            'font': self.button_font,
            'height': 2,
            'width': 15
        }

        self.compile_btn = tk.Button(control_frame, text="开始编译", command=self.compile, **btn_config)
        self.compile_btn.pack(fill=tk.X, pady=10)

        # 分隔线
        separator = tk.Frame(control_frame, height=2, bd=1, relief=tk.SUNKEN)
        separator.pack(fill=tk.X, pady=15)

        self.ast_btn = tk.Button(control_frame, text="显示AST", state=tk.DISABLED,
                                 command=self.show_ast_popup, **btn_config)
        self.ast_btn.pack(fill=tk.X, pady=10)

        self.asm_btn = tk.Button(control_frame, text="显示汇编", state=tk.DISABLED,
                                 command=self.show_asm_popup, **btn_config)
        self.asm_btn.pack(fill=tk.X, pady=10)

        self.clear_btn = tk.Button(control_frame, text="清空页面", command=self.clear_results, **btn_config)
        self.clear_btn.pack(fill=tk.X, pady=10)

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set(" 就绪")
        status_label = tk.Label(control_frame, textvariable=self.status_var,
                                fg="gray", font=self.large_font)
        status_label.pack(side=tk.BOTTOM, pady=(20, 0))

        # 结果交互区（右侧）
        result_frame = tk.Frame(self.window, padx=20, pady=20)
        result_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        # 源代码文本框（上方）
        self.source_text = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            height=24,  # 固定高度
            font=self.code_font,
            padx=10,
            pady=10
        )
        self.source_text.pack(expand=True, fill=tk.BOTH)

        # 分隔线
        separator = ttk.Separator(result_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=5)

        # 输出文本框（下方）
        self.output_text = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            height=6,  # 固定高度
            font=self.code_font,
            padx=10,
            pady=10
        )
        self.output_text.pack(expand=True, fill=tk.BOTH)  # 可扩展填充

        # 配置文本样式
        self.error_font = Font(family="Consolas", size=12, slant="italic", underline=True)
        self.source_text.tag_configure("source", foreground="black")
        self.output_text.tag_configure("output", foreground="black")
        self.output_text.tag_configure("input", foreground="blue")
        self.output_text.tag_configure("error", foreground="red", font=self.error_font)

    def compile(self):
        """处理编译流程"""
        # 获取用户输入
        filename = self.filename_entry.get().strip()

        # 检查文件名是否为空
        if not filename:
            self.show_error("[Error] 请输入源代码文件名")
            return

        # 自动添加.txt后缀
        if not filename.endswith('.txt'):
            filename += '.txt'

        self.last_filename = filename  # 保存当前文件名供后续复用
        self.clear_results()  # 清空旧数据
        self.status_var.set(" 编译中...")  # 更新状态

        try:
            # 读取文件
            if not os.path.exists(filename):
                self.show_error(f"[Error] 文件 {filename} 在当前目录下不存在")
                return

            with open(filename, 'r', encoding='utf-8') as f:
                source = f.read()

            # 显示源代码
            self.source_text.config(state='normal')
            self.source_text.delete(1.0, tk.END)
            lines = source.split('\n')
            for i, line in enumerate(lines, 1):
                self.source_text.insert(tk.END, f"{i:3d} | {line}\n", "source")
            self.source_text.config(state='disabled')

            # 清空输出区域
            self.output_text.config(state='normal')
            self.output_text.delete(1.0, tk.END)
            self.output_text.config(state='disabled')

            # 执行编译
            self.asm_code, self.ast, error_msg = compile_source(source)

            # 关联VM与GUI
            if hasattr(self, 'vm') and self.vm:
                self.vm.gui = self

            if error_msg:
                # 分割多错误信息并分别添加标签
                for err_line in error_msg.split('\n'):
                    if err_line.strip():  # 跳过空行
                        self.show_error(err_line.strip())
                self.status_var.set(" 编译失败")
                # self.ast_btn.config(state=tk.NORMAL)  # 即使编译失败也允许查看AST
                return

            # 更新按钮状态
            self.asm_btn.config(state=tk.NORMAL)
            self.ast_btn.config(state=tk.NORMAL)

            self.status_var.set(f" 编译成功: {os.path.basename(filename)}")

        except Exception as e:
            self.show_error(f"[Error] {str(e)}")
            self.status_var.set(" 编译失败")

    def show_ast_popup(self):
        """在新窗口中显示AST结构"""
        if not self.ast:
            return

        ast_window = tk.Toplevel(self.window)
        ast_window.title(f"AST 结构 - {os.path.basename(self.last_filename)}")

        # 居中显示AST窗口
        window_width = 700
        window_height = 600
        screen_width = ast_window.winfo_screenwidth()
        screen_height = ast_window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        ast_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        text = scrolledtext.ScrolledText(
            ast_window,
            wrap=tk.WORD,
            font=self.code_font,
            padx=15,
            pady=15
        )
        text.pack(expand=True, fill=tk.BOTH)

        # 使用pprint美化AST输出
        ast_str = pprint.pformat(self.ast, indent=2, width=60)
        text.insert(tk.END, ast_str)
        text.config(state='disabled')

    def show_asm_popup(self):
        """在新窗口中显示汇编代码"""
        if not self.asm_code:
            return

        asm_window = tk.Toplevel(self.window)
        asm_window.title(f" 汇编代码 - {os.path.basename(self.last_filename)}")

        # 居中显示汇编窗口
        window_width = 800
        window_height = 600
        screen_width = asm_window.winfo_screenwidth()
        screen_height = asm_window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        asm_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        text = scrolledtext.ScrolledText(
            asm_window,
            wrap=tk.WORD,
            font=self.code_font,
            padx=15,
            pady=15
        )
        text.pack(expand=True, fill=tk.BOTH)

        text.insert(tk.END, self.asm_code)
        text.config(state='disabled')

    def show_error(self, message):
        """在输出框显示错误信息"""
        self.output_text.config(state='normal')
        formatted_msg = message if message.startswith("[Error]") else f"[Error] {message}"  # 添加统一前缀
        self.output_text.insert(tk.END, formatted_msg + "\n", "error")
        self.output_text.see(tk.END)
        self.output_text.config(state='disabled')

    def append_output(self, text):
        """追加输出到结果文本框"""
        self.output_text.config(state='normal')
        self.output_text.insert(tk.END, text + "\n", "output")
        self.output_text.see(tk.END)
        self.output_text.config(state='disabled')

    def clear_results(self):
        """清空所有文本框"""
        self.source_text.config(state='normal')
        self.source_text.delete(1.0, tk.END)
        self.source_text.config(state='disabled')

        self.output_text.config(state='normal')
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state='disabled')

        self.asm_code = None
        self.ast = None
        self.asm_btn.config(state=tk.DISABLED)
        self.ast_btn.config(state=tk.DISABLED)
        self.status_var.set("  就绪")

    def get_input_from_textbox(self):
        """从弹出窗口获取用户输入（用于scanf）"""
        if hasattr(self, 'input_window') and self.input_window and self.input_window.winfo_exists():
            return "0"  # 如果窗口已存在，返回默认值

        self.input_window = tk.Toplevel(self.window)
        self.input_window.title(" 输入请求")

        # 居中显示输入窗口
        window_width = 400
        window_height = 200
        screen_width = self.input_window.winfo_screenwidth()
        screen_height = self.input_window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.input_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 设置窗口为模态
        self.input_window.grab_set()
        self.input_window.transient(self.window)

        input_label = tk.Label(self.input_window, text="请输入scanf需要的值:", font=self.large_font)
        input_label.pack(pady=(20, 10))

        self.input_entry = tk.Entry(self.input_window, font=self.large_font)
        self.input_entry.pack(pady=10, ipady=5)
        self.input_entry.focus_set()

        self.input_result = None

        def on_submit():
            self.input_result = self.input_entry.get()
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, f"{self.input_result}\n", "input")
            self.output_text.see(tk.END)  # 自动滚动到底部
            self.output_text.config(state='disabled')
            self.input_window.destroy()

        submit_btn = tk.Button(self.input_window, text="提交", command=on_submit,
                               font=self.button_font, height=1, width=10)
        submit_btn.pack(pady=10)

        # 绑定回车键
        self.input_entry.bind('<Return>', lambda e: on_submit())

        # 等待窗口关闭
        self.window.wait_window(self.input_window)

        return self.input_result if self.input_result is not None else "0"





# ---------------------------
# 主程序入口
# ---------------------------
if __name__ == "__main__":
    gui = CompilerGUI()
    gui.window.mainloop()