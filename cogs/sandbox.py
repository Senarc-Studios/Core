import aiohttp

from assets.python.internal import Internal

from discord import Interaction, TextStyle, app_commands
from discord.interactions import Interaction
from discord.ui import Button, Modal, View, TextInput
from discord.ext.commands import Cog

from typing import Coroutine, Any

internal = Internal()
Constants = internal.Constants("./assets/json/constants.json")
FETCH_LIST = (
	"EMOJIS",
)
for constant in FETCH_LIST:
	Constants.fetch(constant)

class DeleteResponse(Button):
	def __init__(self, custom_id: str):
		super().__init__(
			style = 4,
			label = "Delete",
			custom_id = custom_id
		)

	async def callback(self, interaction: Interaction) -> Coroutine[Any, Any, None]:
		if self.custom_id != "delete_message":
			key, deletion_token = self.custom_id.split("_")[1:]
			async with aiohttp.ClientSession() as session:
				await session.delete(
					f"https://api.senarc.net/bin/{key}",
					headers = {
						"deletion_token": deletion_token
					}
				)
		await interaction.response.delete_message()

class CodeExecution(Modal, title = "Code Evaluation"):
	code_input = TextInput(
		label = "Code",
		placeholder = "print(\"Hello World!\")",
		style = TextStyle.paragraph,
		required = True
	)

	async def on_submit(self, interaction: Interaction) -> Coroutine[Any, Any, None]:
		EMOJIS = Constants.get("EMOJIS")
		eval_code = (
			EMOJIS["SUCCESS"],
			EMOJIS["WARNING"]
		)
		await interaction.response.defer(
			ephemeral = True,
			thinking = True
		)
		async with aiohttp.ClientSession() as session:
			if code_input.startswith("```py") and code_input.endswith("```"):
				code_input = (code_input[5:])[:3]
			elif code_input.startswith("```") and code_input.endswith("```"):
				code_input = (code_input[3:])[:3]

			async with session.post(
				"https://snekbox.senarc.net/eval",
				json = {
					"input": code_input
				}
			) as response:
				response = await response.json()
				output = response.get('stdout')
				returncode = response.get('returncode')
				output_ = output.split("\n")[:-1]
				modified = False
				count = 0
				_output = ""
				for line in output_:
					count += 1
					_output = _output + f"{(3 - len(str(count)))*'0'}{count} | {line}\n"

				if "```" in _output:
					async with session.post(
						"https://api.senarc.net/paste",
						json = {
							"title": "Snekbox Eval Output",
							"content": output,
							"description": code_input,
							"background_colour": "#1c1e26",
							"text_colour": "#dda487",
							"embed_colour": "#90B5F8"
						}
					) as paste:
						paste = await paste.json()
						full_output = paste.get("url")
						view = View()
						view.add_item(
							Button(style = 5, label = "View Output", url = paste.get("url"))
						)
						view.add_item(
							DeleteResponse(custom_id = f"delete_{paste.get('key')}_{paste.get('deletion_token')}")
						)
						await interaction.response.send_message(
							f"{EMOJIS['WARNING']} Detected attempt to escape code block, output will not be sent in discord.\n\n```py\n{_output}```",
							view = view
						)

				if len(_output.split("\n")) > 20:
					_output = "\n".join(_output.split("\n")[:19])
					_output += "\n[...]"
					async with session.post(
						"https://api.senarc.net/paste",
						json = {
							"title": "Snekbox Eval Output",
							"content": output,
							"description": code_input,
							"background_colour": "#1c1e26",
							"text_colour": "#dda487",
							"embed_colour": "#90B5F8"
						}
					) as paste:
						paste = await paste.json()
						full_output = paste.get("url")
						modified = True

				elif len(output) > 1500 and not modified:
					_output = _output[:1497]
					_output += "..."
					async with session.post(
						"https://api.senarc.net/paste",
						json = {
							"title": "Snekbox Eval Output",
							"content": output,
							"description": code_input,
							"background_colour": "#1c1e26",
							"text_colour": "#dda487",
							"embed_colour": "#90B5F8"
						}
					) as paste:
						paste = await paste.json()
						full_output = paste.get("url")
						modified = True

				if _output.replace("\n", "") == "":
					_output = "[No output]"

				if returncode == 0:
					message = f"{eval_code[0]} Successfully executed code."

				else:
					message = f"{eval_code[1]} Code execution returned code `{returncode}`."

				if modified:
					view = View()
					view.add_item(
						Button(style = 5, label = "Full Output", url = full_output)
					)
					view.add_item(
						DeleteResponse(custom_id = f"delete_{paste.get('key')}_{paste.get('deletion_token')}")
					)
					await interaction.response.send_message(
						f"{message}\n\n```py\n{_output}```",
						view = view
					)

				else:
					view = View()
					view.add_item(
						DeleteResponse(custom_id = f"delete_message")
					)
					await interaction.response.send_message(
						f"{message}\n\n```py\n{_output}```",
						view = view
					)

class Sandbox(Cog):
	def __init__(self, bot):
		self.bot = bot

	@app_commands.command(
		name = "eval",
		description = "Evaluate your Python code.",
		options = [
			app_commands.CommandOption(
				name = "code",
				description = "The code to evaluate. (or enter nothing)",
			)
		]
	)
	async def eval_(self, interaction: Interaction, code: str = None) -> Coroutine[Any, Any, None]:
		if code is None:
			modal = CodeExecution()
			await interaction.response.send_modal(modal)
		else:
			try:
				await interaction.response.send_message(eval(code))
			except Exception as error:
				await interaction.response.send_message(error)

async def setup(bot):
	await bot.add_cog(Sandbox(bot))