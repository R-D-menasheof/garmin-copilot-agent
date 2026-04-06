using 'main.bicep'

param baseName = 'vitalis'
param location = 'swedencentral'
param vitalisApiKey = readEnvironmentVariable('VITALIS_API_KEY', '')
