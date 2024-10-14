#!/usr/bin/env python3

import re, ast, argparse, glob
from lxml import etree

TEST_MODE = None

def equals_operator(field, value):
    if isinstance(value, bool):
        return field if value else f"not {field}"
    else:
        return f"{field} == {repr(value)}"

def not_equals_operator(field, value):
    if isinstance(value, bool):
        return f"not {field}" if value else field
    else:
        return f"{field} != {repr(value)}"


class AttrsParser:
    OPERATORS = {
        '=': equals_operator,
        '!=': not_equals_operator,
        'in': lambda field, value: f"{field} in {value}",
        'not in': lambda field, value: f"{field} not in {value}",
        ">": lambda field, value: f"{field} > {repr(value)}",
        "<": lambda field, value: f"{field} < {repr(value)}",
        ">=": lambda field, value: f"{field} >= {repr(value)}",
        "<=": lambda field, value: f"{field} <= {repr(value)}",
    }


    def __init__(self, xml_path: str) -> None:
        self.xml_path = xml_path
        self.has_xml_declaration = False
        self.__read_xml()

    def __read_xml(self):
        with open(self.xml_path, 'r') as f:
            xml_content = f.read()
        return xml_content

    def __write_xml(self, xml_content):
        if TEST_MODE:
            return
        with open(self.xml_path, 'w') as f:
            f.write(xml_content)

    def preprocess(self):
        """
        The pre-processing of the script consist in :
        - Checking if XML file contains an xml declaration
        - Adding single quotes around the %(...)d so that they can be interpreted
        """
        xml_content = self.__read_xml()

        self.has_xml_declaration = xml_content.startswith('<?xml')
        self.xml_declaration_double_quote = '<?xml version="1.0"' in xml_content
        xml_content = re.sub(r'(%\([a-zA-Z_.]+\))d', r"'\1d'", xml_content)
        
        self.__write_xml(xml_content)

    def postprocess(self):
        """
        The post-processing of the script consist in :
        - Removing the single quotes around the %(...)d so they are back to their original state
        - Converts the single quotes in the XML declaration to double quotes
        """
        xml_content = self.__read_xml()

        xml_content = re.sub(r"'(%\([a-zA-Z_.]+\)d)'", r"\1", xml_content)
        if self.has_xml_declaration and self.xml_declaration_double_quote:
            index = xml_content.find('?>')
            # Split the content into declaration and the rest
            declaration, rest = xml_content[:index+2], xml_content[index+2:]
            declaration = declaration.replace("'", '"')
            xml_content = declaration + rest

        self.__write_xml(xml_content)

    def __convert_prefix_to_python_expression(self, prefix):
        """
        Converts a prefix expression to a python expression. By default, if no operator is specified, it will be considered as an AND
        Example : 
        - [('locked', '=', True)] -> locked
        - [('artisan_task', '=', False)] -> not artisan_task
        - [('artisan_task', '=', False), ('locked', '=', True)] -> not artisan_task and locked
        - ['|', ('artisan_task', '=', False), ('state', 'in', ['cancel', 'pre_cancel'])] -> not artisan_task or state in ['cancel', 'pre_cancel']
        - [('incident_type', 'not in', ['preventive', 'op'])] -> incident_type not in ['preventive', 'op']

        /!\ For this one, it will first add single quotes around the %(...)d, then remove them once parsed. They cannot be parsed as is because
        they are not a valid python expression
        - ['|', ('partner_id', '=', False),
                '|', ('stage_id', 'not in', [%(custom_module.new_request)d, %(custom_module.new_quotation)d]),
                    ('complete_status', 'not in', ['2', '3'])
        -> not partner_id or stage_id not in [%(custom_module.new_request)d, %(custom_module.new_quotation)d] or complete_status not in ['2', '3']
        """
        stack = []
        if prefix in [0, 1]:
            return str(bool(prefix))
        for token in reversed(prefix):
            if isinstance(token, tuple):
                stack.append(AttrsParser.OPERATORS[token[1]](token[0], token[2]))
            elif token in ['&', '|']:
                left = stack.pop()
                op = 'and' if token == '&' else 'or'
                right = stack.pop()
                stack.append(f"({left} {op} {right})")
        while len(stack) > 1:  # Handle implicit '&' operators
            right = stack.pop()
            left = stack.pop()
            stack.append(f"({left} and {right})")
        print("Adapted", prefix, "to", stack[0])
        return stack[0] if stack else ''

    def __convert_and_update(self, element):
        """
        Converts an etree.Element to the Odoo 17 notation that does not support 'attrs'. It will convert both
        <field name="something" attrs={...}/> and <attribute name="attrs"/> to the new notation
        """
        if element.tag == "attribute":
            if not element.text:
                print(f"WARNING: {self.xml_path.split('/')[-1]}:{element.sourceline}: has no 'attrs' value, it must be adapted manually")
                return
            for attribute, value in ast.literal_eval(element.text.strip()).items():
                element.attrib["name"] = attribute
                element.text = self.__convert_prefix_to_python_expression(value)
        else:
            for attribute, value in ast.literal_eval(element.get("attrs").strip()).items():
                element.set(attribute, self.__convert_prefix_to_python_expression(value))

            del element.attrib["attrs"]

    def convert_attrs(self):
        # Must parse since the XML declaration at the start of the string does not allow us to parse the string directly
        root = etree.parse(self.xml_path).getroot()
        for element in root.xpath("//*[@attrs] | //attribute[@name='attrs']"):
            self.__convert_and_update(element)

        xml_content = etree.tostring(root, encoding='utf-8', pretty_print=True, xml_declaration=self.has_xml_declaration).decode('utf-8')
        self.__write_xml(xml_content)

    def convert_column_invisible(self):
        # Must parse since the XML declaration at the start of the string does not allow us to parse the string directly
        root = etree.parse(self.xml_path).getroot()
        for element in root.xpath("//tree//field[@invisible]"):
            element.attrib["column_invisible"] = "True" if element.attrib["invisible"] == "1" else "False"
            del element.attrib["invisible"]
        
        xml_content = etree.tostring(root, encoding='utf-8', pretty_print=True, xml_declaration=self.has_xml_declaration).decode('utf-8')
        self.__write_xml(xml_content)

    def process_xml(self):
        self.preprocess()
        self.convert_attrs()
        self.convert_column_invisible()
        self.postprocess()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert infix expression to python expression')
    parser.add_argument('xml_paths', type=str, nargs='+', help='The path(s) of the XML file(s) to parse')
    parser.add_argument('--test', type=bool, nargs='?', help='Run the script without replacing the files')

    args = parser.parse_args()

    TEST_MODE = args.test
    if TEST_MODE:
        print("WARNING: Test mode enabled, the execution won't affect any file")

    for xml_path_pattern in args.xml_paths:
        for xml_path in glob.glob(xml_path_pattern):
            parser = AttrsParser(xml_path)
            parser.process_xml()
