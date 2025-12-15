{ lib
, python311
, fetchFromGitHub
, stdenv
, cudaPackages ? null
, enableCuda ? true
}:

let
  python = python311.override {
    packageOverrides = self: super: {
      # Override packages as needed for TabbyAPI compatibility
    };
  };

  pythonEnv = python.withPackages (ps: with ps; [
    # Core dependencies
    fastapi
    uvicorn
    pydantic
    pyyaml
    jinja2
    aiohttp
    httpx
    packaging
    rich

    # ML dependencies
    torch
    safetensors
    sentencepiece
    transformers
    tokenizers

    # ExLlamaV2 (built separately)
    # exllamav2

    # Additional
    numpy
    tqdm
  ]);
in
stdenv.mkDerivation rec {
  pname = "tabbyapi";
  version = "0.1.0";

  src = fetchFromGitHub {
    owner = "theroyallab";
    repo = "tabbyAPI";
    rev = "main";  # Pin to specific commit in production
    sha256 = lib.fakeSha256;  # Replace with actual hash
  };

  nativeBuildInputs = [
    python
  ];

  buildInputs = [
    pythonEnv
  ] ++ lib.optionals enableCuda [
    cudaPackages.cudatoolkit
    cudaPackages.cudnn
  ];

  installPhase = ''
    mkdir -p $out/bin $out/lib/tabbyapi

    # Copy source
    cp -r . $out/lib/tabbyapi/

    # Create wrapper script
    cat > $out/bin/tabbyapi << EOF
    #!${stdenv.shell}
    export PYTHONPATH="$out/lib/tabbyapi:\$PYTHONPATH"
    exec ${pythonEnv}/bin/python -m main "\$@"
    EOF
    chmod +x $out/bin/tabbyapi
  '';

  meta = with lib; {
    description = "OpenAI-compatible exllamav2 API server";
    homepage = "https://github.com/theroyallab/tabbyAPI";
    license = licenses.agpl3Only;
    platforms = platforms.linux;
  };
}
