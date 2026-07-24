targetScope = 'resourceGroup'

@description('Monthly cost budget in USD')
param amount int = 10

@description('Email address for budget alerts')
param contactEmail string

@description('Budget start date (first of a month, YYYY-MM-DD)')
param startDate string = '2026-03-01'

// Cost guardrail: alerts as spend approaches the ~$10/mo target.
resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: 'vitalis-monthly'
  properties: {
    category: 'Cost'
    amount: amount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: startDate
      endDate: '2029-12-01'
    }
    notifications: {
      actual_80: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        contactEmails: [ contactEmail ]
        thresholdType: 'Actual'
      }
      actual_100: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        contactEmails: [ contactEmail ]
        thresholdType: 'Actual'
      }
      forecast_100: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        contactEmails: [ contactEmail ]
        thresholdType: 'Forecasted'
      }
    }
  }
}
