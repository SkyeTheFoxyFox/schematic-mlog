# Schematic Mlog
aka "schemlog" or "mschml"

It's a parser to convert an mlog like language to mindustry schematics.

# Running the script
You'll need `pymsch` to run the script, you can get it with `pip install pymsch`.

Then just run the script with some arguments.
 
 - `-src <path>`
	Defines the source file. (required)
 - `-out <path>`
	Defines the output file. (optional, if excluded it won't output a file)
 - `-copy`
	Enables clipboard output.

# Instructions

## `schem`
  
  This instruction opens a schematic scope.

  `schem codeName "in game name" "in game description"`
  
  Close a schematic scope with `endschem`

  The in game name and description are optional, and really only apply to the `Main` schem.

  At least 1 schematic named `Main` required, this is the one that gets exported, all others are optional.

## `label`
  
  This instruction adds a text tag to the schematic.

  `label "a text label"`

## `block`
  
  This instruction adds a block to the open schematic.

  `block codeName content-name x y rotation`

  x, y, and rotation are optional, if they're excluded it will try to fit the block wherever it can (left to right, bottom to top) with a rotation of 0.

  If rotation is excluded it will set the rotation to 0.

## `bounds`
  
  This instruction sets the maximum area that can be filled with automatically positioned blocks, the default is 64 x 64.

  `bounds width height`

## `config`
  
  This instruction sets the config of a block.

  `config type blockName value ...`

  the valid types are
  - `string`
    
    Sets the config to a string, for message blocks.
  - `content`
   
    Sets the config to a content type, such as `copper` or `titanium-wall`.
  - `point`
    
    Sets the config to a point for blocks that only have one connection.

    If supplied 2 numbers it writes that as a relative position from the block.
    
    If supplied a blockName it writes the point that connects them.

  - `appendpoint`
    
    Just like `point`, but it stores a list of points for blocks that have many connections.
    
    If ran more than once the further points get appended.
    
  - `none`
    
    Sets the config to nothing.
    
## `link`
  
  This instruction adds a link to a processor.

  `link processorName linkName targetName`
  
  `link processorName linkName x y`

  `linkName` doesn't really matter as the game will determine it on it's own when building the schematic, but it can be useful for keeping track of stuff.

  if using a point the x and y are relative to the block.
  
## `proc`
  
  This instruction sets the code of a proc.

  `proc procName`

  If ran without arguments it will read all the lines until it finds an `endproc` and write them as the processor's code.

  `proc procName file1 ...`

  If ran with file arguments it will read the files and concatenate them together before writing them directly to the processor.
 
 ## `compileproc`
 
  This instruction is like `proc` however it takes a second argument for a build script, and doesn't support file imports.
	
  `compileproc procName buildScript`

  The build scripts have to be an importable python file (so either a package, or a file in the same directory), and must contain a `build` function that will take in a string for the code input, and will return a string of mlog code. 
