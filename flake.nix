{
  description = "NeoscopeBuddy - Reproducible Python zipapp build environment";

  inputs = {
    nixpkgs.url = "https://flakehub.com/f/DeterminateSystems/nixpkgs-26.05-chilled/0.1";
  };

  outputs = {
    self,
    nixpkgs,
  }: let
    forAllSystems = nixpkgs.lib.genAttrs ["x86_64-linux"];

    # Source of truth for version. Nix ships a TOML parser as a builtin,
    # so there's no need to hand-roll a regex against pyproject.toml.
    # Assumes a PEP 621 `[project]` table (uv-managed projects have this).
    version = (builtins.fromTOML (builtins.readFile ./pyproject.toml)).project.version;

    # zip stores timestamps as DOS dates, which can't represent anything
    # before 1980-01-01 — zip silently clamps earlier dates to that floor.
    # Epoch 1 (1970) was clamped too, so it wasn't buying any determinism
    # it didn't already have; pin it to the real floor instead.
    epoch = 315532800;

    # Read Python version from .python-version. nixpkgs only publishes
    # major.minor attrs (python314, not python3140), so truncate any patch
    # component, and trim more than just trailing "\n" while we're at it.
    pyVerParts = nixpkgs.lib.take 2 (
      nixpkgs.lib.splitString "." (nixpkgs.lib.trim (builtins.readFile ./.python-version))
    );
    pyVerAttr = "python" + builtins.concatStringsSep "" pyVerParts;

    mkPkgs = system: import nixpkgs {inherit system;};
    py = pkgs: pkgs.${pyVerAttr};

    # zipapp bundles source only, no third-party deps. If runtime deps are
    # ever needed, vendor site-packages into `staging` before zipping.
    mkZipapp = pkgs:
      pkgs.stdenvNoCC.mkDerivation {
        name = "nscb.pyz";

        nativeBuildInputs = with pkgs; [
          coreutils
          findutils
          gnused
          zip
        ];

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

          find staging -type f -exec chmod 644 {} +
          find staging -type d -exec chmod 755 {} +
          find staging -exec touch -d "@${toString epoch}" {} +

          (cd staging && find . \( -type d -o -type f \) | LC_ALL=C sort | zip -X -q -@ ../archive.zip)

          cat ${./src/polyglot.sh} > $out
          cat archive.zip >> $out
          chmod +x $out
        '';
      };

    # $bin wrapper so the pyz is installable on $PATH by home-manager / NixOS
    # (the raw pyz output is a file, not a directory). The pyz keeps its
    # polyglot `#!/bin/sh` shim (LD_PRELOAD save/strip before python runs;
    # python3 resolved from PATH, see src/polyglot.sh) so the artifact is
    # byte-identical everywhere (reproducible). This wrapper execs the shim
    # under the store bash with PATH pinned to the store-pinned python3 and
    # coreutils (env, readlink), which is what NixOS home-manager needs —
    # the shim still runs, then python executes the archive.
    mkNscb = pkgs: zipapp:
      pkgs.runCommand "nscb" {
        nativeBuildInputs = [pkgs.makeWrapper];
        passthru = {inherit zipapp;};
      } ''
        mkdir -p $out/bin $out/libexec
        cp ${zipapp} $out/libexec/nscb.pyz
        makeWrapper ${pkgs.bash}/bin/bash $out/bin/nscb \
          --prefix PATH : ${pkgs.coreutils}/bin \
          --prefix PATH : ${py pkgs}/bin \
          --add-flags "$out/libexec/nscb.pyz"
      '';
  in {
    packages = forAllSystems (system: let
      pkgs = mkPkgs system;
      zipapp = mkZipapp pkgs;
    in {
      default = zipapp;
      nscb = mkNscb pkgs zipapp;
    });

    homeModules.default = {pkgs, ...}: {
      home.packages = [self.packages.${pkgs.system}.nscb];
    };
    nixosModules.default = {pkgs, ...}: {
      environment.systemPackages = [self.packages.${pkgs.system}.nscb];
    };

    devShells = forAllSystems (system: let
      pkgs = mkPkgs system;
    in {
      # Standard `devShells.<system>.default` shape so `nix develop` resolves it
      # (and not the default package).
      default = pkgs.mkShell {
        name = "neoscopebuddy";

        packages =
          (with pkgs; [
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
          ])
          ++ [(py pkgs)];

        shellHook = ''
          echo "NeoscopeBuddy development environment loaded"
          echo "Python: $(${py pkgs}/bin/python3 --version)"
          echo ""
          echo "Build with: make build  (local)"
          echo "Nix build: nix build    (reproducible)"
        '';
      };
    });
  };
}
