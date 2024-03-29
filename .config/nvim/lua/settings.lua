local o = vim.o
local wo = vim.wo

local utils = require "utils"
local theme = require "themes.theme"

vim.g.mapleader = " "

vim.g.vim_jsx_pretty_colorful_config = 1
vim.cmd [[set fcs=eob:\ ]]
vim.cmd [[filetype plugin indent on]]

vim.g.BASH_Ctrl_j = 'off'

--Markdown preview config

vim.g.mkdp_auto_start = 1
vim.g.mkdp_auto_close = 1
vim.g.mkdp_refresh_slow = 1



-- vim.cmd[[highlight Normal guibg=NONE ctermbg=NONE]]

local options = {
    writebackup = false,
    wrap = true,
    termguicolors = true,
    fileencoding = "utf-8",
    backup = false,
    swapfile = false,
    hlsearch = true,
    incsearch = true,
    showmode = false,
    expandtab = true,
    shiftwidth = 2,
    tabstop = 2,
    scrolloff = 5,
    sidescrolloff = 5,
    smartindent = true,
    signcolumn = "yes",
    hidden = true,
    ignorecase = true,
    timeoutlen = 1000,
    shiftround = true,
    smartcase = true,
    splitbelow = true,
    splitright = true,
    number = true,
    relativenumber = true,
    clipboard = "unnamedplus",
    cursorline = true,
    mouse = "a",
    cmdheight = 1,
    undodir = "/tmp/.nvimdid",
    undofile = true,
    pumheight = 10,
    laststatus = 3,
    updatetime = 250,
    background = "dark",
    showmatch = true,
    modifiable = true,
}

vim.opt.shortmess:append "c"

for key, value in pairs(options) do
    vim.opt[key] = value
end

utils.setSpacesSize { go = 4, python = 4, rust = 4, cpp = 4, c = 4 }

theme.init()
