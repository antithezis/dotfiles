---@type vim.lsp.Config
return {
	on_init = function(client)
		-- Rename is handled by vtsls (through the Angular tsserver plugin);
		-- keeping it here too makes the rename prompt show up twice.
		client.server_capabilities.renameProvider = false
	end,
}
