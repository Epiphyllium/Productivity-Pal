# Prodctivity Pal

## Overview

Productivity pal now

## Quick Start

1. **Set Up Python Environment and Install Dependencies of OS-Copilot**

2. **Other Dependencies:**

   ```shell
   python -m pip install "pymongo[srv]"
   pip install --quiet sentence-transformers pymongo einops
   npm install electron
   ```

3. **Set OpenAI API Key:** Configure your OpenAI API key in .env

4. **Set Mongodb Atlas:** Replace `<username>`, `<password>`, and `<cluster-url>` with your Atlas credentials in `CONNECTION_STRING` in .env

   ```shell
   CONNECTION_STRING = "mongodb+srv://<username>:<password>@<cluster-url>/myDatabase?retryWrites=true&w=majority"
   ```

5. **Start server and front-end interface**
   ```shell
   cd productivity_pal
   python server.py #server
   npm start #front-end interface
   ```

   

