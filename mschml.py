from pymsch import Schematic, Block, Content, ContentLists, Point, PointArray, ProcessorConfig, ProcessorLink
import sys, importlib

INPUT_FILE = ""
OUTPUT_FILE = ""
OUTPUT_CLIPBOARD = False

def ERROR(message, line):
	print(f"ERROR at line {line}:", message)
	sys.exit()

def WARNING(message, line):
	print(f"WARNING at line {line}:", message)

def GLOBAL_ERROR(message):
	print(f"ERROR:", message)
	sys.exit()

def ins_arg_check(ins, length):
	if(len(ins.args) < length):
		ERROR(f"Instruction '{ins.instruction}' expected more arguments", ins.line_number)

def require_schem(ins, schem):
	if(schem == None):
		ERROR(f"Instruction '{ins.instruction}' expected an open schematic", ins.line_number)

def not_string(ins, arg):
	if(arg[0] == '"'):
		ERROR("Unexpected string", ins.line_number)
	else:
		return(arg)

def maybe_string(arg):
	if(arg[0] == '"'):
		return(arg[1:len(arg)-1])
	else:
		return(arg)

def str_to_content(ins, arg):
	try:
		content = getattr(Content, arg.upper().replace("-", "_"))
	except AttributeError:
		ERROR(f"Unknown content type '{arg}'", ins.line_number)
	return(content)

def str_to_block(ins, arg):
	content = str_to_content(ins, arg)
	if(content in ContentLists.BLOCKS):
		return(content)
	else:
		ERROR(f"Block expected, found '{arg}'", ins.line_number)

class Instruction:
	def __init__(self, instruction, args, line_number):
		self.instruction = instruction
		self.args = args
		self.line_number = line_number

	def __repr__(self):
		return(f"instruction: '{self.instruction}', args: {self.args}, line: {self.line_number}")

class MschmlFile:

	class Line:
		def __init__(self, data, line_number):
			self.data = data
			self.line_number = line_number

	def __init__(self, file_loc):
		self.current_line = 0
		try:
			self.data = open(file_loc, "r").read()
		except OSError:
			GLOBAL_ERROR(f"Can't find file '{file_loc}'", )

	def take_line(self):
		try:
			line, self.data = self.data.split('\n', 1)
		except ValueError:
			line = self.data
			self.data = ""
		self.current_line += 1
		line = self.Line(line, self.current_line)
		return(line)

	def get_instruction_line(self):
		line = self.take_line()
		line = self.Line(line.data.strip("\t "), line.line_number)
		while(line.data == '' or line.data[0] == '#'):
			line = self.take_line()
			line = self.Line(line.data.strip("\t "), line.line_number)
		return(self.remove_end_line_comments(line))

	def remove_end_line_comments(self, line):
		output_line = ""
		in_string = False
		for char in line.data:
			if(char == '"'):
				in_string = not in_string
				output_line += char
			elif(char == '#' and in_string == False):
				break
			else:
				output_line += char
		if(in_string == True):
			ERROR("String not closed", line.line_number)
		return(self.Line(output_line, line.line_number))

	def split_instruction_line(self, line):
		arg_list = []
		arg = ""
		in_string = False
		for char in line:
			if(char == '"'):
				in_string = not in_string
				arg += char
			elif(char == ' ' and in_string == False):
				arg_list.append(arg)
				arg = ""
			else:
				arg += char
		arg_list.append(arg)
		return(arg_list)

	def get_instruction(self):
		line = self.get_instruction_line()
		ins = self.split_instruction_line(line.data)
		return(Instruction(ins[0], ins[1:], line.line_number))

class MschmlSchem(Schematic):
	def __init__(self, name):
		self.tiles = []
		self.tags = {}
		self.labels = []
		self.filled_list = []
		self.bounds = (64, 64)
		self.name = name
		self.named_tiles = {}

	def copy(self):
		a = Schematic()
		a.tiles = self.tiles.copy()
		a.tags = self.tags.copy()
		a.labels = self.labels.copy()
		a.filled_list = self.filled_list.copy()
		a.bounds = self.bounds
		a.name = self.name
		a.named_tiles = self.named_tiles.copy()
		return(a)

class Instructions:
	def __call__(self, ins_input):
		ins = ins_input.instruction
		try:
			if('__' in ins):
				ERROR(f"Unknown instruction '{ins}'", ins_input.line_number)
			else:
				getattr(Instructions, ins)(ins_input)
		except AttributeError:
			ERROR(f"Unknown instruction '{ins}'", ins_input.line_number)
	
	def schem(ins):
		ins_arg_check(ins, 1)
		global current_schem
		if(current_schem != None):
			ERROR(f"Instruction 'schem' cannot be used within an open schematic scope. Did you mean 'placeschem'?", ins.line_number)
		current_schem = MschmlSchem(not_string(ins, ins.args[0]))
		current_schem.name = not_string(ins, ins.args[0])
		if(len(ins.args) >= 2):
			current_schem.set_tag('name', maybe_string(ins.args[1]))
		if(len(ins.args) >= 3):
			current_schem.set_tag('description', maybe_string(ins.args[2]))

	def endschem(ins):
		global current_schem
		global known_schems
		require_schem(ins, current_schem)

		known_schems[current_schem.name] = current_schem.copy()
		current_schem = None

	def placeschem(ins):
		ins_arg_check(ins, 3)
		global current_schem
		global known_schems
		require_schem(ins, current_schem)

		if(ins.args[0] not in known_schems):
			ERROR(f"Unknown schematic '{ins.args[0]}'", ins.line_number)

		current_schem.add_schem(known_schems[ins.args[0]], int(ins.args[1]), int(ins.args[2]))

	def bounds(ins):
		ins_arg_check(ins, 2)
		global current_schem
		require_schem(ins, current_schem)

		current_schem.bounds = (int(ins.args[0]), int(ins.args[1]))

	def label(ins):
		ins_arg_check(ins, 1)
		global current_schem
		require_schem(ins, current_schem)

		current_schem.add_label(maybe_string(ins.args[0]))

	def block(ins):
		ins_arg_check(ins, 2)
		global current_schem
		require_schem(ins, current_schem)

		block_type = str_to_block(ins, ins.args[1])

		if(len(ins.args) > 2):
			ins_arg_check(ins, 4)
			if(len(ins.args) > 4):
				ins_arg_check(ins, 5)
				block = current_schem.add_block(Block(block_type, int(ins.args[2]), int(ins.args[3]), None, int(ins.args[4])))
				if(block == None):
					WARNING(f"Block '{ins.args[0]}' doesn't fit at ({int(ins.args[2])}, {int(ins.args[3])}), skipping", ins.line_number)
				else:
					current_schem.named_tiles[not_string(ins, ins.args[0])] = block
			else:
				block = current_schem.add_block(Block(block_type, int(ins.args[2]), int(ins.args[3]), None, 0))
				if(block == None):
					WARNING(f"Block '{ins.args[0]}' doesn't fit at ({int(ins.args[2])}, {int(ins.args[3])}), skipping", ins.line_number)
				else:
					current_schem.named_tiles[not_string(ins, ins.args[0])] = block
		else:
			size = block_type.value.size
			min_x = (size - 1) // 2
			min_y = (size - 1) // 2
			max_x = current_schem.bounds[0] - (size // 2)
			max_y = current_schem.bounds[1] - (size // 2)

			if(max_x >= 0 and max_y >= 0):
				for y in range(min_y, max_y):
					for x in range(min_x, max_x):
						block = current_schem.add_block(Block(block_type, x, y, None, 0))
						if(block != None):
							current_schem.named_tiles[not_string(ins, ins.args[0])] = block
							return
			WARNING(f"Block '{ins.args[0]}' doesn't fit within the defined bounds ({current_schem.bounds[0]}, {current_schem.bounds[1]}), skipping", ins.line_number)
						
	def config(ins):
		ins_arg_check(ins, 2)
		global current_schem
		require_schem(ins, current_schem)

		if(ins.args[1] not in current_schem.named_tiles):
			ERROR(f"Block '{ins.args[1]}' not found", ins.line_number)
		src_block = current_schem.named_tiles[not_string(ins, ins.args[1])]

		class ConfigArgs:
			def string():
				ins_arg_check(ins, 3)
				src_block.set_config(maybe_string(ins.args[2]))

			def content():
				ins_arg_check(ins, 3)
				src_block.set_config(str_to_content(ins, ins.args[2]))

			def point():
				ins_arg_check(ins, 3)
				if(len(ins.args) > 3):
					src_block.set_config(Point(int(ins.args[3]), int(ins.args[4])))
				else:
					if(ins.args[2] in current_schem.named_tiles):
						if(ins.args[2] not in current_schem.named_tiles):
							ERROR(f"Block '{ins.args[2]}' not found", ins.line_number)
						x_src = src_block.x
						y_src = src_block.y
						x_dest = current_schem.named_tiles[ins.args[2]].x
						y_dest = current_schem.named_tiles[ins.args[2]].y
						src_block.set_config(Point(x_dest - x_src, y_dest - y_src))
					else:
						ERROR(f"Block '{ins.args[2]}' not found", ins.line_number)

			def appendpoint():
				ins_arg_check(ins, 3)

				if(type(src_block.config).__name__ != 'PointArray'):
					src_block.config = PointArray()

				if(len(ins.args) > 3):
					src_block.config.append(Point(int(ins.args[3]), int(ins.args[4])))
				else:
					if(ins.args[2] in current_schem.named_tiles):
						if(ins.args[2] not in current_schem.named_tiles):
							ERROR(f"Block '{ins.args[2]}' not found", ins.line_number)
						x_src = src_block.x
						y_src = src_block.y
						x_dest = current_schem.named_tiles[ins.args[2]].x
						y_dest = current_schem.named_tiles[ins.args[2]].y
						src_block.config.append(Point(x_dest - x_src, y_dest - y_src))
					else:
						ERROR(f"Block '{ins.args[2]}' not found", ins.line_number)

			def none():
				src_block.set_config(None)

		try:
			if('__' in ins.args[0]):
				ERROR(f"Unknown 'config' subinstruction '{ins.args[0]}'", ins.line_number)
			else:
				getattr(ConfigArgs, ins.args[0])()
		except AttributeError:
			ERROR(f"Unknown 'config' subinstruction '{ins.args[0]}'", ins.line_number)

		# if(len(ins.args) > 2):
			# current_schem.named_tiles[not_string(ins, ins.args[0])].set_config(Point(int(ins.args[2]), int(ins.args[3])))
		# elif(ins.args[1][0] == '"'):
			# current_schem.named_tiles[not_string(ins, ins.args[0])].set_config(maybe_string(ins.args[1]))
		# elif(ins.args[1] in current_schem.named_tiles):
			# x_src = current_schem.named_tiles[ins.args[0]].x
			# y_src = current_schem.named_tiles[ins.args[0]].y
			# x_dest = current_schem.named_tiles[ins.args[1]].x
			# y_dest = current_schem.named_tiles[ins.args[1]].y
			# current_schem.named_tiles[not_string(ins, ins.args[0])].set_config(PointArray([Point(x_dest - x_src, y_dest - y_src)]))
		# else:
			# current_schem.named_tiles[not_string(ins, ins.args[0])].set_config(str_to_content(ins, ins.args[1]))
	
	def link(ins):
		ins_arg_check(ins, 3)
		global current_schem
		require_schem(ins, current_schem)

		if(ins.args[0] not in current_schem.named_tiles):
			ERROR(f"Block '{ins.args[0]}' not found", ins.line_number)
		if(current_schem.named_tiles[ins.args[0]].block not in [Content.MICRO_PROCESSOR, Content.LOGIC_PROCESSOR, Content.HYPER_PROCESSOR, Content.WORLD_PROCESSOR]):
			ERROR(f"'Processor expected, found{ins.args[0]}'", ins.line_number)

		proc = current_schem.named_tiles[ins.args[0]]

		if(type(proc.config).__name__ != 'ProcessorConfig'):
			proc.config = ProcessorConfig("", [])

		if(len(ins.args) > 3):
			proc.config.links.append(ProcessorLink(int(ins.args[2]), int(ins.args[2]), maybe_string(ins.args[1])))
		else:
			if(ins.args[2] not in current_schem.named_tiles):
				ERROR(f"Block '{ins.args[2]}' not found", ins.line_number)
			x_src = current_schem.named_tiles[ins.args[0]].x
			y_src = current_schem.named_tiles[ins.args[0]].y
			x_dest = current_schem.named_tiles[ins.args[2]].x
			y_dest = current_schem.named_tiles[ins.args[2]].y
			proc.config.links.append(ProcessorLink(x_dest - x_src, y_dest - y_src, maybe_string(ins.args[1])))

	def proc(ins):
		ins_arg_check(ins, 1)
		global current_schem
		require_schem(ins, current_schem)

		if(ins.args[0] not in current_schem.named_tiles):
			ERROR(f"Block '{ins.args[0]}' not found", ins.line_number)
		if(current_schem.named_tiles[ins.args[0]].block not in [Content.MICRO_PROCESSOR, Content.LOGIC_PROCESSOR, Content.HYPER_PROCESSOR, Content.WORLD_PROCESSOR]):
			ERROR(f"'Processor expected, found{ins.args[0]}'", ins.line_number)

		proc = current_schem.named_tiles[ins.args[0]]

		if(type(proc.config).__name__ != 'ProcessorConfig'):
			proc.config = ProcessorConfig("", [])

		code = ""

		if(len(ins.args) > 1):
			for file in ins.args[1:]:
				try:
					code += open(maybe_string(file)).read() + '\n'
				except OSError:
					ERROR(f"Can't find file '{maybe_string(file)}'", ins.line_number)
		else:
			global main_file
			line = main_file.get_instruction_line()
			while(main_file.data != "" and main_file.split_instruction_line(line.data)[0] != "endproc"):
				code += line.data + '\n'
				line = main_file.get_instruction_line()
			if(main_file.data == ""):
				ERROR(f"Failed to find 'endproc' instruction", ins.line_number)

		proc.config.code = code

	def compileproc(ins):
		ins_arg_check(ins, 2)
		global current_schem
		require_schem(ins, current_schem)

		if(ins.args[0] not in current_schem.named_tiles):
			ERROR(f"Block '{ins.args[0]}' not found", ins.line_number)
		if(current_schem.named_tiles[ins.args[0]].block not in [Content.MICRO_PROCESSOR, Content.LOGIC_PROCESSOR, Content.HYPER_PROCESSOR, Content.WORLD_PROCESSOR]):
			ERROR(f"'Processor expected, found{ins.args[0]}'", ins.line_number)

		proc = current_schem.named_tiles[ins.args[0]]

		if(type(proc.config).__name__ != 'ProcessorConfig'):
			proc.config = ProcessorConfig("", [])

		code = ""

		global main_file
		line = main_file.take_line()
		while(main_file.data != "" and main_file.split_instruction_line(line.data.strip('\t '))[0] != "endproc"):
			code += line.data + '\n'
			line = main_file.take_line()
		if(main_file.data == ""):
			ERROR(f"Failed to find 'endproc' instruction", ins.line_number)
		try:
			module = importlib.import_module(maybe_string(ins.args[1]))
		except ModuleNotFoundError:
			ERROR(f"Can't find module '{maybe_string(ins.args[1])}'", ins.line_number)
		try:
			proc.config.code = module.build(code)
		except AttributeError:
			ERROR(f"No 'build' function found in '{maybe_string(ins.args[1])}'", ins.line_number)
		except TypeError:
			ERROR(f"'build' function expected to have 1 argument", ins.line_number)

	def endproc(ins):
		global current_schem
		require_schem(ins, current_schem)
		ERROR(f"Instruction 'endproc' expected an open processor", ins.line_number)

class Arguments:
	def __init__(self, argv):
		self.args = argv[1:].copy()

		self.__handle_args__()

	def __pop_arg__(self):
		try:
			return(self.args.pop(0))
		except IndexError:
			return(None)

	def __handle_args__(self):
		while(self.args != []):
			arg = self.__pop_arg__()
			if(arg[0] != '-'):
				GLOBAL_ERROR(f"Expected '-' at the beginning of argument")
			arg = arg[1:]
			try:
				if('__' in arg):
					GLOBAL_ERROR(f"Unknown argument '{arg}'")
				else:
					getattr(Arguments, arg)(self)
			except AttributeError:
				GLOBAL_ERROR(f"Unknown argument '{arg}'")

	def src(self):
		global INPUT_FILE
		INPUT_FILE = self.__pop_arg__()
		if(INPUT_FILE == None):
			GLOBAL_ERROR(f"Argument 'src' expected another value")

	def out(self):
		global OUTPUT_FILE
		OUTPUT_FILE = self.__pop_arg__()
		if(INPUT_FILE == None):
			GLOBAL_ERROR(f"Argument 'out' expected another value")

	def copy(self):
		global OUTPUT_CLIPBOARD
		OUTPUT_CLIPBOARD = True

Arguments(sys.argv)

main_file = MschmlFile(INPUT_FILE)

current_schem = None
known_schems = {}

while(main_file.data != ""):
	Instructions()(main_file.get_instruction())
if(current_schem != None):
	GLOBAL_ERROR(f"Schematic '{current_schem.name}' not closed")
try:
	if(OUTPUT_CLIPBOARD):
		known_schems['Main'].write_clipboard()
	if(OUTPUT_FILE != ""):
		known_schems['Main'].write_file(OUTPUT_FILE)
except KeyError:
	GLOBAL_ERROR("Can't find schamatic with the name 'Main'")
print("done")