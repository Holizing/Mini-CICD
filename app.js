const express = require('express')

const app = express()
const port = Number(process.env.PORT || 3000)

app.get('/', (_request, response) => {
  response.json({
    application: 'mini-cicd-express-demo',
    status: 'healthy',
  })
})

app.get('/health', (_request, response) => {
  response.json({ status: 'healthy' })
})

app.listen(port, '127.0.0.1', () => {
  console.log(`Express demo listening on ${port}`)
})
