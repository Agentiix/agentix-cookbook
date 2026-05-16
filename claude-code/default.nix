# System deps for the agentix.claude_code namespace.
#
# `agentix build` runs this derivation in a builder stage and symlinks
# the resulting `bin/*` into the namespace's `/nix/claude_code/bin/`
# inside the bundle image. The namespace worker's PATH is prepended
# with that bin/, so user code can call `claude` and `git` by bare name.
#
# Only system binaries belong here. The Python package itself is
# installed into the namespace's venv by `pip install`, not by Nix.
{ pkgs ? import <nixpkgs> { config.allowUnfree = true; } }:

let
  claude = pkgs.stdenv.mkDerivation (finalAttrs: {
    pname = "claude-code";
    version = "2.1.114";

    src = pkgs.fetchurl {
      url = "https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases/${finalAttrs.version}/linux-x64/claude";
      hash = "sha256-Er1LCRbesGvhf/x7LwSF4UC/ALLbPct4Rp1mcj1zwn8=";
    };

    dontUnpack = true;
    dontStrip = true;

    nativeBuildInputs = [ pkgs.makeWrapper ];

    installPhase = ''
      runHook preInstall
      install -Dm755 $src $out/bin/claude
      runHook postInstall
    '';

    postFixup = ''
      wrapProgram $out/bin/claude \
        --argv0 claude \
        --set DISABLE_AUTOUPDATER 1 \
        --set-default DISABLE_NON_ESSENTIAL_MODEL_CALLS 1 \
        --set DISABLE_INSTALLATION_CHECKS 1
    '';

    meta = {
      description = "Anthropic Claude Code CLI";
      homepage = "https://claude.ai/code";
      license = pkgs.lib.licenses.unfree;
      mainProgram = "claude";
      platforms = [ "x86_64-linux" ];
    };
  });
in
pkgs.symlinkJoin {
  name = "agentix-claude-code-deps";
  paths = [ claude pkgs.git ];
}
