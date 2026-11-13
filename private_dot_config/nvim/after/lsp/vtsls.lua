---@type vim.lsp.Config
return {
	on_attach = function(client)
		if client and client.server_capabilities.semanticTokensProvider then
			client.server_capabilities.semanticTokensProvider.range = false
		end
	end,
	settings = {
		complete_function_calls = true,
		vtsls = {
			enableMoveToFileCodeAction = true,
			autoUseWorkspaceTsdk = true,
			tsserver = {
				globalPlugins = {
					-- Angular support inside .ts files (templates, inputs, etc.)
					{
						name = "@angular/language-server",
						location = vim.fn.stdpath("data")
							.. "/mason/packages/angular-language-server/node_modules/@angular/language-server",
						enableForWorkspaceTypeScriptVersions = false,
					},
				},
			},
			experimental = {
				maxInlayHintLength = 30,
				completion = {
					enableServerSideFuzzyMatch = true,
				},
			},
		},
		typescript = {
			updateImportsOnFileMove = { enabled = "always" },
			suggest = {
				completeFunctionCalls = true,
			},
			preferences = {
				useAliasesForRenames = false,
			},
			inlayHints = {
				enumMemberValues = { enabled = true },
				functionLikeReturnTypes = { enabled = true },
				parameterNames = { enabled = "literals" },
				parameterTypes = { enabled = true },
				propertyDeclarationTypes = { enabled = true },
				variableTypes = { enabled = false },
			},
		},
	},
}
