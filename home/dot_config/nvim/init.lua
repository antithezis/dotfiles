if vim.loader then
	vim.loader.enable()
end

-- _G.dd = function(...)
--     require("util.debug").dump(...)
-- end
-- vim.print = _G.dd

_G.Antithezis = require("antithezis.utils")
require("antithezis.config.options")
require("antithezis.config.keymaps")
require("antithezis.config.autocmds")
require("antithezis.config.commands")
require("antithezis.config.workarounds")
require("antithezis.plugins")
