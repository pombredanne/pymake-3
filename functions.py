
# davep 20-Mar-2016 ; built-in functions

import sys
import logging

logger = logging.getLogger("pymake.functions")
logger.setLevel(level=logging.DEBUG)

from symbol import VarRef, Literal
from evaluate import evaluate
from vline import VCharString
from error import *
import shell

__all__ = [ "Info", 
			"MWarning",
			"Error",
			"Shell", 

			"make_function",
		  ]

# built-in functions GNU Make 3.81(ish?)
builtins = {
	"subst",
	"patsubst",
	"strip",
	"findstring",
	"filter",
	"filter-out",
	"sort",
	"word",
	"words",
	"wordlist",
	"firstword",
	"lastword",
	"dir",
	"notdir",
	"suffix",
	"basename",
	"addsuffix",
	"addprefix",
	"join",
	"wildcard",
	"realpath",
	"absname",
	"error",
	"warning",
	"shell",
	"origin",
	"flavor",
	"foreach",
	"if",
	"or",
	"and",
	"call",
	"eval",
	"file",
	"value",
	"info",
}

class Function(VarRef):
	def __init__(self, args):
		logger.debug("function=%s args=%s", self.name, args)
		super().__init__(args)

	def makefile(self):
		s = "$(" + self.name + " "
		for t in self.token_list : 
			s += t.makefile()
		s += ")"
		return s

	def eval(self, symbol_table):
		return ""

class PrintingFunction(Function):
	def eval(self, symbol_table):
		s = evaluate(self.token_list, symbol_table)
		logger.debug("%s \"%s\"", self.name, s)
		print(s, file=self.fh)
		return ""

class Info(PrintingFunction):
	name = "info"
	fh = sys.stdout

class MWarning(PrintingFunction):
	# name Warning is used by Python builtins so use MWarning instead
	name = "warning"
	fh = sys.stderr

	def eval(self, symbol_table):
		logger.debug("self=%s", self)
		t = self.token_list[0]
		s = evaluate(self.token_list, symbol_table)
		print("{}:{}: {}".format(t.string[0].filename, t.string[0].linenumber, s), file=self.fh)
		return ""

class Error(PrintingFunction):
	name = "error"
	fh = sys.stderr

	def eval(self, symbol_table):
		logger.debug("self=%s", self)

		t = self.token_list[0]

		s = evaluate(self.token_list, symbol_table)
		print("{}:{}: *** {}. Stop.".format(t.string[0].filename, t.string[0].linenumber, s), file=self.fh)
		sys.exit(1)

class Subst(Function):
	name = "subst"
	
	def eval(self, symbol_table):
		# needs 3 args
		logger.debug("%s len=%d tokens=%s", self.name, len(self.token_list), self.token_list)
		for t in self.token_list:
			print(t)
			if t.string:
				s = t.string
				for c in s:
					print("type={} pos={} filename={}".format(type(c), c.pos, c.filename))

		raise Unimplemented

		s = "".join([t.eval(symbol_table) for t in self.token_list])
		logger.debug("%s s=\"%s\"", self.name, s)
		# make skips whitpace between subst and first art
		s = s.lstrip()
		logger.debug("%s s=\"%s\"", self.name, s)
		c1 = s.index(',')
		from_ = s[:c1]
		s = s[c1+1:]
		c2 = s.index(',')
		to = s[:c2]
		text = s[c2+1:]

		logger.debug("%s from=\"%s\" to=\"%s\" text=\"%s\"", self.name, from_, to, text)
		s = text.replace(from_, to)
		logger.debug("%s \"%s\"", self.name, s)
		return s

class Shell(Function):
	name = "shell"

	def eval(self, symbol_table):
		s = "".join([t.eval(symbol_table) for t in self.token_list])
		logger.debug("%s s=\"%s\"", self.name, s)
		return shell.execute(s)

def split_function_call(s):
	# break something like "info hello world" that needs a secondary parse
	# into a proper looking function call
	#
	# "info hello, world" -> "info", "hello, world"
	# "info" -> "info"
	# "info  hello, world" -> "info", " hello, world"
	# "info\thello, world" -> "info", "hello, world"

	logger.debug("split s=\"%s\" len=%d", s, len(s))
	state_init = 0
	state_searching = 1

	iswhite = lambda c : c==" " or c=="\t"

	state = state_init

	# Find first whitespace, split the string into string before and after
	# whitespace, throwing away the whitespace itself.
	for idx, vchar in enumerate(s):
		c = vchar.char
		logger.debug("c=%s state=%d idx=%d", c, state, idx)
		# most common state first
		if state==state_searching:
			# we have seen at least one non-white so now seeking a next
			# whitespace
			if iswhite(c):
				# don't return empty string, return None if there is nothing
				logger.debug("s=\"%s\" idx=%d", s, idx)
				return VCharString(s[:idx]), VCharString(s[idx+1:]) if idx+1<len(s) else None
		elif state==state_init:
			if iswhite(c):
				# no functions start with whitespace
				return s, None
			else:
				state = state_searching

	# no whitespace anywhere
	return s, None

_classes = {
	"info" : Info,
	"warning" : MWarning,
	"error" : Error,
	"subst" : Subst,
	"shell" : Shell,
}

def make_function(arglist):
	logger.debug("make_function arglist=%s", arglist)

	for a  in arglist:
		print(a)

	# do NOT .eval() here!!! will cause side effects. only want to look up the string
	vcstr = arglist[0].string
	# .string will be a VCharString
	# do NOT modify arglist; is a ref into the AST

	fname, rest = split_function_call(vcstr)

	logger.debug("make_function fname=\"%s\" rest=\"%s\"", fname, rest)

	# convert from array to python string for lookup
	fname = str(fname)

	# allow KeyError to propagate to indicate this is not a function
	fcls = _classes[fname]

	logger.debug("make_function fname=\"%s\" rest=\"%s\" fcls=%s", fname, rest, fcls)

	if rest: return fcls([Literal(rest)] + arglist[1:])
	return fcls(arglist[1:])
