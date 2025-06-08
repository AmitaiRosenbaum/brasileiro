import { Autocomplete, TextField } from "@mui/material";
import Layout from "./Layout";

function App() {
  return (
    <Layout>
      <Autocomplete
        disablePortal
        options={[1, 2, 3]}
        fullWidth
        renderInput={(params) => (
          <TextField {...params} label="Search for a song" />
        )}
      />
    </Layout>
  );
}

export default App;
