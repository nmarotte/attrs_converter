# XML Infix to Python Expression Converter
This Python script is designed to convert infix expressions in XML files to Python expressions. It is particularly useful for transforming certain attributes in XML files into more readable and manageable Python expressions.

## Features
- Converts infix expressions to Python expressions.
- Supports the following operators: =, !=, in, not in.
- Parses XML files and updates the attributes of elements based on the converted expressions.

## How to Use
* Clone this repository to your local machine.
* Navigate to the directory containing the script.
* Run the script using the following command:
```
python attrs_parser.py <xml_path1> <xml_path2> ...
```
Replace <xml_path1> <xml_path2> ... with the paths (or wildcard) to the XML files you want to parse.

e.g. : 
```
python attrs_parser.py custom_modules/views/view1.xml custom_modules/views/view2.xml
python attrs_parser.py custom_modules/**/views/*.xml
```
### Example
Consider the following XML file:
```XML
<root>
    <element attrs="{'invisible': [('artisan_task', '=', False)], 'readonly': [('locked', '=', True)]}"/>
</root>
```
Running the script on this file will result in:
```XML
<root>
    <element invisible="not artisan_task" readonly="locked"/>
</root>
```
## Dependencies

See requirements.txt

## Limitations
This script is designed to work with specific XML structures and may not work as expected with all XML files. It is recommended to backup your XML files before using the script to replace them.
