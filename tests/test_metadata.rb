require "yaml"

root = File.expand_path("..", __dir__)
config = YAML.safe_load(File.read(File.join(root, "doover_device", "config.yaml")))
translations = YAML.safe_load(
  File.read(File.join(root, "doover_device", "translations", "en.yaml"))
)

required = %w[name version slug description arch options schema]
missing = required.reject { |key| config.key?(key) }
raise "missing add-on keys: #{missing.join(', ')}" unless missing.empty?

raise "unsupported architecture declared" unless config.fetch("arch").sort == %w[aarch64 amd64]
raise "Docker API access must be declared" unless config["docker_api"]
raise "Home Assistant API access must be declared" unless config["homeassistant_api"]
raise "'boot' should be omitted when it uses the auto default" if config["boot"] == "auto"
raise "'host_network' should be omitted when it uses the false default" if config["host_network"] == false
raise "'protected' is an install setting, not app metadata" if config.key?("protected")

option_keys = config.fetch("options").keys.sort
schema_keys = config.fetch("schema").keys.sort
translation_keys = translations.fetch("configuration").keys.sort
raise "options and schema differ" unless option_keys == schema_keys
raise "options and translations differ" unless option_keys == translation_keys

puts "add-on metadata: ok"
