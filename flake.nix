{
  description = "NeoscopeBuddy - Reproducible Python zipapp build environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (
      system: let
        pkgs = nixpkgs.legacyPackages.${system};
        # Read Python version from .python-version file (strip newline and dot)
        pythonVersion = builtins.replaceStrings ["\n"] [""] (builtins.readFile ./.python-version);
        pythonAttr = builtins.replaceStrings ["."] [""] pythonVersion;
        python = pkgs."python${pythonAttr}";
      in {
        devShells.default = pkgs.mkShell {
          name = "neoscopebuddy";

          packages = with pkgs; [
            bashInteractive
            coreutils
            findutils
            gawk
            git
            gnugrep
            gnused
            gnutar
            jq
            less
            prettier
            python
            rsync
            uv
            which
            zip
          ];

          shellHook = ''
            export PYTHON=${python}/bin/python3

            # Set SOURCE_DATE_EPOCH for reproducible builds if not already set
            export SOURCE_DATE_EPOCH=''${SOURCE_DATE_EPOCH:-315532800}

            echo "NeoscopeBuddy development environment loaded"
            echo "Python: $(python --version)"
            echo "SOURCE_DATE_EPOCH: $SOURCE_DATE_EPOCH"
            echo ""
            echo "Build with: make build"
            echo "The Makefile sets SOURCE_DATE_EPOCH for reproducible builds"
          '';
        };
      }
    );
}
