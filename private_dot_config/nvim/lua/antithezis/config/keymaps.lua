local keymap = vim.keymap
local opts = { noremap = true, silent = true }

-- Do things without updating the registers
keymap.set("n", "x", '"_x')
keymap.set("n", "<Leader>p", '"0p')
keymap.set("n", "<Leader>P", '"0P')
keymap.set("v", "<Leader>p", '"0p')
keymap.set("n", "<Leader>c", '"_c')
keymap.set("n", "<Leader>C", '"_C')
keymap.set("v", "<Leader>c", '"_c')
keymap.set("v", "<Leader>C", '"_C')
keymap.set("n", "<Leader>d", '"_d')
keymap.set("n", "<Leader>D", '"_D')
keymap.set("v", "<Leader>d", '"_d')
keymap.set("v", "<Leader>D", '"_D')

-- Increment/decrement
keymap.set("n", "+", "<C-a>")
keymap.set("n", "-", "<C-x>")

-- Delete a word backwards
keymap.set("n", "dw", 'vb"_d')

-- Select all (<Esc>/<C-c>/y leave visual mode and restore the previous cursor position)
keymap.set("n", "<C-a>", function()
	local buf = vim.api.nvim_get_current_buf()
	local view = vim.fn.winsaveview()
	local restore_keys = {
		["<Esc>"] = function()
			return vim.keycode("<Esc>")
		end,
		["<C-c>"] = function()
			return vim.keycode("<Esc>")
		end,
		["y"] = function()
			return '"' .. vim.v.register .. "y" -- keep "+y, "ay, etc.
		end,
	}

	local function cleanup()
		for lhs in pairs(restore_keys) do
			pcall(vim.keymap.del, "x", lhs, { buffer = buf })
		end
	end

	for lhs, get_keys in pairs(restore_keys) do
		keymap.set("x", lhs, function()
			local keys = get_keys()
			cleanup()
			vim.api.nvim_feedkeys(keys, "nx", false)
			vim.fn.winrestview(view)
		end, { buffer = buf, nowait = true, desc = "Leave select all and restore cursor" })
	end

	-- Remove the temporary mappings once visual mode ends any other way (y, d, >, ...)
	vim.api.nvim_create_autocmd("ModeChanged", {
		callback = function()
			if not vim.fn.mode():match("^[vV\22]") then
				cleanup()
				return true -- delete this autocmd
			end
		end,
	})

	vim.cmd("normal! ggVG")
end, { desc = "Select all" })

-- Disable continuations
keymap.set("n", "<Leader>o", "o<Esc>^Da", opts)
keymap.set("n", "<Leader>O", "O<Esc>^Da", opts)

-- Jumplist
keymap.set("n", "<C-m>", "<C-i>", opts)

-- New tab
keymap.set("n", "te", ":tabedit<CR>")
keymap.set("n", "<tab>", ":tabnext<CR>", opts)
keymap.set("n", "<s-tab>", ":tabprev<CR>", opts)
-- Split window
keymap.set("n", "ss", ":split<Return>", opts)
keymap.set("n", "sv", ":vsplit<Return>", opts)
-- Move window
keymap.set("n", "sh", "<C-w>h")
keymap.set("n", "sk", "<C-w>k")
keymap.set("n", "sj", "<C-w>j")
keymap.set("n", "sl", "<C-w>l")

-- Toggle inlay hints
keymap.set("n", "<leader>i", function()
	-- require("antithezis.lsp").toggleInlayHints()
end)

-- Yank current file path
keymap.set("n", "<leader>yf", function()
	require("antithezis.utils.editor").yank_relative_path_with_line()
end, { desc = "Yank relative path with line number" })

keymap.set("n", "<leader>yp", function()
	require("antithezis.utils.editor").yank_absolute_path_with_line()
end, { desc = "Yank absolute path with line number" })

keymap.set("v", "<leader>cc", ":<C-u>lua require('antithezis.utils.editor').copy_as_codeblock()<CR>")

keymap.set("n", "<leader>j", function()
	require("antithezis.utils.editor").open_package_json()
end, { desc = "Open package.json in floating window" })

keymap.set("n", "<leader>bd", function()
	require("antithezis.utils.editor").delete_hidden_buffers()
end, { desc = "Delete hidden buffers" })
