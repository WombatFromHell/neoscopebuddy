{
  description = "NeoscopeBuddy - Reproducible Python zipapp build environment";

  inputs = {
    nixpkgs.url = "https://flakehub.com/f/DeterminateSystems/nixpkgs-26.05-chilled/0.1";
  };

  outputs = {
    self,
    nixpkgs,
  }: let
    version = let
      m = builtins.match ".*\nversion = \"([^\"]+)\".*" ("\n" + builtins.readFile ./pyproject.toml);
    in
      if m != null
      then builtins.head m
      else throw "Version not found in pyproject.toml";

    epoch = 1;

    pyVerRaw = builtins.replaceStrings ["\n"] [""] (builtins.readFile ./.python-version);
    pyVerAttr = "python" + builtins.replaceStrings ["."] [""] pyVerRaw;

    forAllSystems = nixpkgs.lib.genAttrs ["x86_64-linux" "aarch64-linux"];

    mkOutputs = system: let
      pkgs = import nixpkgs {inherit system;};
      py = pkgs.${pyVerAttr};

      zipapp = pkgs.stdenvNoCC.mkDerivation {
        name = "nscb.pyz";
        nativeBuildInputs = [pkgs.coreutils pkgs.findutils pkgs.gnused pkgs.zip];
        dontUnpack = true;
        dontInstall = true;
        dontPatchShebangs = true;
        buildPhase = ''
          mkdir -p staging
          cp -r ${./src}/. staging
          rm -f staging/polyglot.sh
          chmod -R u+w staging

          sed -i 's/^__version__ = .*/__version__ = "${version}"/' \
            "staging/nscb/application.py"
          echo "from entry import main; main()" > staging/__main__.py

          find staging -type d -exec chmod 755 {} +
          find staging -type f -exec chmod 644 {} +
          find staging -exec touch -d "@${toString epoch}" {} +

          (cd staging && find . \( -type d -o -type f \) | LC_ALL=C sort | zip -X -q -@ archive.zip)

          cat ${./src/polyglot.sh} > $out
          cat staging/archive.zip >> $out
          chmod +x $out
        '';
      };

      nscb =
        pkgs.runCommand "nscb" {
          nativeBuildInputs = [pkgs.gnused];
          passthru = {inherit zipapp;};
        } ''
          mkdir -p $out/bin
          sed 's|/usr/bin/python3|${py}/bin/python3|' ${zipapp} > $out/bin/nscb
          chmod +x $out/bin/nscb
        '';
    in {
      packages = {
        default = zipapp;
        inherit nscb;
      };
      devShell = pkgs.mkShell {
        name = "neoscopebuddy";
        packages = with pkgs; [
          bashInteractive
          coreutils
          findutils
          ripgrep
          jq
          less
          prettier
          rsync
          util-linux
          uv
          which
          zip
          py
        ];
        shellHook = ''
          echo "NeoscopeBuddy development environment loaded"
          echo "Python: $(${py}/bin/python3 --version)"
          echo ""
          echo "Build with: make build  (local)"
          echo "Nix build: nix build    (reproducible)"
        '';
      };
    };

    perSystem = forAllSystems mkOutputs;
  in {
    packages = forAllSystems (system: perSystem.${system}.packages);
    devShells = forAllSystems (system: {default = perSystem.${system}.devShell;});

    nixosModules.default = {pkgs, ...}: {
      environment.systemPackages = [self.packages.${pkgs.system}.nscb];
    };
    homeModules.default = {pkgs, ...}: {
      home.packages = [self.packages.${pkgs.system}.nscb];
    };
  };
}
