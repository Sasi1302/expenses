import { z } from 'zod';

export const validate = (schema) => (req, res, next) => {
  console.log("schema",schema)
  
  try {
    schema.parse({
      body: req.body,
      query: req.query,
      params: req.params,
    });
    next();
  } catch (error) {
    console.log(error)
    if (error.name === 'ZodError' || error instanceof z.ZodError) {
      const issues = error.issues || error.errors || [];
      const messages = issues.map(err => err.message);
      return res.status(400).json({ error: messages.length ? messages.join(', ') : error.message });
    }
    next(error);
  }
};
