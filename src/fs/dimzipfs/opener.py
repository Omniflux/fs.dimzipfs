__all__ = ['DIMZipOpener']

from fs.opener import Opener
from fs.opener.errors import NotWriteable, OpenerError
from fs.opener.parse import ParseResult

from .dimzipfs import DIMZipFS

class DIMZipOpener(Opener):
	"""`DIMZipFS` opener."""

	protocols = ['dimzip']

	def open_fs(self, fs_url: str, parse_result: ParseResult, writeable: bool, create: bool, cwd: str) -> DIMZipFS:
		if create or writeable:
			raise NotWriteable("Unable to open DAZ Install Manager package for writing")

		try:
			return DIMZipFS(parse_result.resource)  # type: ignore
		except Exception as e:
			raise OpenerError(f'Could not open DAZ Install Manager package: {e}')