# -*- coding: utf-8 -*-
"""Kit için yalın giriş: ana uygulamada `PEMF_Backend.exe --alt-surec modul-surucu <klasör>` ile AYNI yol (sunucu / port AÇILMAZ)."""
import sys


def main(argv=None) -> int:
    av = list(sys.argv[1:] if argv is None else argv)
    if not av or av[0] != "--alt-surec":
        print("kullanım: backend_service.py --alt-surec modul-surucu <modül klasörü>", file=sys.stderr)
        return 2
    from servers.alt_surec import calistir

    return calistir(av[1:])


if __name__ == "__main__":
    raise SystemExit(main())
