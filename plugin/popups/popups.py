"""Incapsulate popup creation."""

import sublime
import mdpopups
import logging

from ..utils.macro_parser import MacroParser

POPUP_CSS_FILE = "Packages/EasyClangComplete/plugin/popups/popup.css"

log = logging.getLogger("ECC")

MD_TEMPLATE = """!!! {type}
    {contents}
"""

CODE_TEMPLATE = """```{lang}
{code}
```\n"""

DECLARATION_TEMPLATE = """## Declaration: ##
{type_declaration}
"""


class Popup:
    """Incapsulate popup creation."""

    WRAPPER_CLASS = "ECC"
    MAX_POPUP_WIDTH = 1800
    MAX_POPUP_HEIGHT = 800

    def __init__(self):
        """Initialize basic needs."""
        self.CSS = sublime.load_resource(POPUP_CSS_FILE)

    @staticmethod
    def error(text):
        """Initialize a new error popup."""
        popup = Popup()
        popup.__popup_type = 'panel-error "ECC: Error"'
        popup.__text = text
        return popup

    @staticmethod
    def warning(text):
        """Initialize a new warning popup."""
        popup = Popup()
        popup.__popup_type = 'panel-warning "ECC: Warning"'
        popup.__text = text
        return popup

    @staticmethod
    def info(cursor, cindex, settings):
        """Initialize a new warning popup."""
        popup = Popup()
        popup.__popup_type = 'panel-info "ECC: Info"'

        type_decl = [
            cindex.CursorKind.STRUCT_DECL,
            cindex.CursorKind.UNION_DECL,
            cindex.CursorKind.CLASS_DECL,
            cindex.CursorKind.ENUM_DECL,
            cindex.CursorKind.TYPEDEF_DECL,
            cindex.CursorKind.CLASS_TEMPLATE,
            cindex.CursorKind.TYPE_ALIAS_DECL,
            cindex.CursorKind.TYPE_REF
        ]

        # Initialize the text the declaration.
        declaration_text = ''

        # Show the return type of the function/method if applicable,
        # macros just show that they are a macro.
        macro_parser = None
        is_macro = cursor.kind == cindex.CursorKind.MACRO_DEFINITION
        is_type = cursor.kind in type_decl
        if is_macro:
            macro_parser = MacroParser(cursor.spelling, cursor.location)
            declaration_text += '\#define '
        else:
            if cursor.result_type.spelling:
                result_type = cursor.result_type
            elif cursor.type.spelling:
                result_type = cursor.type
            else:
                result_type = None
                log.warning("No spelling for type provided in info.")
                return ""

            if cursor.is_static_method():
                declaration_text += "static "

            if cursor.spelling != cursor.type.spelling:
                # Don't show duplicates if the user focuses type, not variable
                declaration_text += Popup.link_from_location(
                    Popup.location_from_type(result_type),
                    result_type.spelling)

        # Link to declaration of item under cursor
        if cursor.location:
            declaration_text += Popup.link_from_location(cursor.location,
                                                         cursor.spelling)
        else:
            declaration_text += cursor.spelling

        # Macro/function/method arguments
        args_string = None
        if is_macro:
            # cursor.get_arguments() doesn't give us anything for macros,
            # so we have to parse those ourselves
            args_string = macro_parser.args_string
        else:
            args = []
            for arg in cursor.get_arguments():
                if arg.spelling:
                    args.append(arg.type.spelling + ' ' + arg.spelling)
                else:
                    args.append(arg.type.spelling + ' ')
            if cursor.kind in [cindex.CursorKind.FUNCTION_DECL,
                               cindex.CursorKind.CXX_METHOD]:
                args_string = '('
                if len(args):
                    args_string += ', '.join(args)
                args_string += ')'
        if args_string:
            declaration_text += args_string

        # Show value for enum
        if cursor.kind == cindex.CursorKind.ENUM_CONSTANT_DECL:
            declaration_text += " = " + str(cursor.enum_value)
            declaration_text += "(" + hex(cursor.enum_value) + ")"

        # Method modifiers
        if cursor.is_const_method():
            declaration_text += " const"

        popup.__text = DECLARATION_TEMPLATE.format(
            type_declaration=declaration_text)

        # Show macro body
        if is_macro:
            popup.__text += "### Body:\n"
            popup.__text += CODE_TEMPLATE.format(
                lang="c++", code=macro_parser.body_string)
        # Doxygen comments
        if cursor.brief_comment:
            popup.__text += "### Brief documentation:\n"
            popup.__text += CODE_TEMPLATE.format(lang="",
                                                 code=cursor.brief_comment)
        if cursor.raw_comment:
            popup.__text += "### Full doxygen comment:\n"
            popup.__text += CODE_TEMPLATE.format(
                lang="", code=Popup.cleanup_comment(cursor.raw_comment))
        # Show type declaration
        if settings.show_type_body and is_type and cursor.extent:
            body = Popup.get_text_by_extent(cursor.extent)
            popup.__text += "### Body:\n"
            popup.__text += CODE_TEMPLATE.format(lang="c++", code=body)
        return popup

    def as_markdown(self):
        """Represent all the text as markdown."""
        tabbed_text = "\n\t".join(self.__text.split('\n'))
        return MD_TEMPLATE.format(type=self.__popup_type,
                                  contents=tabbed_text)

    def show(self, view, location=-1, on_navigate=None):
        """Show this popup."""
        mdpopups.show_popup(view, self.as_markdown(),
                            max_width=Popup.MAX_POPUP_WIDTH,
                            max_height=Popup.MAX_POPUP_HEIGHT,
                            wrapper_class=Popup.WRAPPER_CLASS,
                            css=self.CSS,
                            location=location,
                            on_navigate=on_navigate)

    @staticmethod
    def cleanup_comment(raw_comment):
        """Cleanup raw doxygen comment."""
        def pop_prepending_empty_lines(lines):
            first_non_empty_line_idx = 0
            for line in lines:
                if line == '':
                    first_non_empty_line_idx += 1
                else:
                    break
            return lines[first_non_empty_line_idx:]

        import string
        lines = raw_comment.split('\n')
        chars_to_strip = '/' + '*' + string.whitespace
        lines = [line.lstrip(chars_to_strip) for line in lines]
        lines = pop_prepending_empty_lines(lines)
        clean_lines = []
        is_brief_comment = True
        for line in lines:
            if line == '' and is_brief_comment:
                # Skip lines that belong to brief comment.
                is_brief_comment = False
                continue
            if is_brief_comment:
                continue
            clean_lines.append(line)
        return '\n'.join(clean_lines)

    @staticmethod
    def location_from_type(clang_type):
        """Return location from type.

        Return proper location from type.
        Remove all inderactions like pointers etc.

        Args:
            clang_type (cindex.Type): clang type.

        """
        cursor = clang_type.get_declaration()
        if cursor and cursor.location and cursor.location.file:
            return cursor.location

        cursor = clang_type.get_pointee().get_declaration()
        if cursor and cursor.location and cursor.location.file:
            return cursor.location

        return None

    @staticmethod
    def link_from_location(location, text):
        """Provide link to given cursor.

        Transforms SourceLocation object into markdown string.

        Args:
            location (Cursor.location): Current location.
            text (str): Text to be added as info.
        """
        result = ""
        if location and location.file and location.file.name:
            result += "[" + text + "]"
            result += "(" + location.file.name
            result += ":" + str(location.line)
            result += ":" + str(location.column)
            result += ") "
        else:
            result += text + ' '
        return result

    @staticmethod
    def get_text_by_extent(extent):
        """Load lines of code in range, pointed by extent.

        Args:
            extent (Cursor.extent): Ranges of source file.
        """
        if extent.start.file.name != extent.end.file.name:
            return None

        with open(extent.start.file.name, 'r') as f:
            lines = f.readlines()
            return "".join(lines[extent.start.line - 1:extent.end.line])

    @staticmethod
    def build_objc_message_info_details(cursor):
        """Provide information about cursor to Objective C message expression.

        Builds detailed information about cursor when cursor is
        a CursorKind.OBJC_MESSAGE_EXPR. OBJC_MESSAGE_EXPR cursors
        behave very differently from other C/C++ cursors in that:
        - The return type we want to show in the tooltip
          is stored in the original 'cursor.type' from the cursor the user is
          hovering over; in C/C++ we only used 'cursor.referenced' but nothing
          else from the original cursor.
        - 'cursor.referenced' is still important, as it holds the name and args
          of the method being called in the message. But
          'cursor.referenced.spelling' comes in a different format then what
          For example, if we have this method declaration for 'bar':
            @interface Foo
              -(void)bar:(BOOL)b1 boolParam2:(BOOL):b2
            @end
          And later, we hover over the text calling bar():
            Foo* foo = [[Foo alloc] init];
            [foo bar:YES boolParam2:NO]; // <- Hover over 'bar' here
          Then we would see:
            cursor.kind = CursorKind.OBJC_INSTANCE_METHOD_DECL
            cursor.type.spelling = 'void'
            cursor.referenced.kind: CursorKind.OBJC_INSTANCE_METHOD_DECL
            cursor.referenced.spelling = 'bar:boolParam2:'
            cursor.referenced.arguments[0].type.spelling = 'BOOL'
            cursor.referenced.arguments[0].spelling = 'b1'
            cursor.referenced.arguments[1].spelling = 'BOOL'
            cursor.referenced.arguments[1].spelling = 'b2'
          Our goal is to make the tooltip match the method declaration:
            'void bar:(BOOL)b1 boolParam2:(BOOL):b2'
        - Objective C methods also don't need to worry about static/const

        Args:
            cursor (Cursor): Current cursor.
        """
        result = ""
        return_type = cursor.type
        result += Popup.link_from_location(
            Popup.location_from_type(return_type),
            return_type.spelling)

        result += ' '

        method_cursor = cursor.referenced
        method_and_params = method_cursor.spelling.split(':')
        method_name = method_and_params[0]
        if method_cursor.location:
            result += Popup.link_from_location(
                method_cursor.location,
                method_name)
        else:
            result += method_cursor.spelling

        method_params_index = 1
        for arg in method_cursor.get_arguments():
            result += ":(" + arg.type.spelling + ")"
            if arg.spelling:
                result += arg.spelling + " "
            result += method_and_params[method_params_index]
            method_params_index += 1

        if method_cursor.brief_comment:
            result += "<br><br><b>"
            result += method_cursor.brief_comment + "</b>"

        return result
