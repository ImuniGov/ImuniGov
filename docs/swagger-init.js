SwaggerUIBundle({
  url: "/docs/openapi.json",
  dom_id: "#swagger-ui",
  deepLinking: true,
  presets: [
    SwaggerUIBundle.presets.apis,
    SwaggerUIBundle.SwaggerUIStandalonePreset
  ],
  layout: "BaseLayout",
  defaultModelsExpandDepth: 1,
  defaultModelExpandDepth: 2,
  docExpansion: "list",
  filter: true,
  tryItOutEnabled: true
});
