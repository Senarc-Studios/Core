class Internal:
	def __init__(self):
		class Constants:
			def __init__(self, constants_file: str):
				self.constants_file = constants_file
				self.cache = {}

			def fetch(self, key: str) -> Any:
				with open(self.constants_file, "r") as file:
					constants = json.load(file)
					
				self.cache.update(
					{
						key: constants[key]
					}
				)
				return self.constants.get(key)

			def get(self, key: str) -> Any:
				return self.cache.get(key)
