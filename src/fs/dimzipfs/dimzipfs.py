"""Manage the filesystem in a DAZ Install Manager package."""
from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from typing import Any, Collection, Mapping, NoReturn
	from fs.info import RawInfo
	from fs.permissions import Permissions
	from typing import BinaryIO

from pathlib import Path

from fs import errors
from fs._url_tools import url_quote
from fs.base import FS
from fs.info import Info
from fs.memoryfs import MemoryFS
from fs.path import abspath
from fs.zipfs import ReadZipFS
from lxml import etree

class DIMZipFS(FS):
	"""Read DAZ Install Manager packages filtered by package manifest.

	DAZ Install Manager packages are zip files. See `fs.zipfs.ZipFS` for more details.

	Arguments:
		file (str or io.IOBase): An OS filename, or an open file object.

	Raises:
		`fs.errors.CreateFailed`: If duplicate files exist in TARGET, Manifest.dsx cannot be opened or parsed,
		or if ZipFS raises an error.
	"""

	@errors.CreateFailed.catch_all  # type: ignore
	def __init__(self, file: BinaryIO | str) -> None:
		super().__init__()
		self._file = file
		self._manifestfs = MemoryFS()
		self._zipFS = ReadZipFS(file)

		with self._zipFS.openbin('Manifest.dsx') as f:
			manifest_tree = etree.parse(f)
			for e in manifest_tree.xpath(f"/DAZInstallManifest/File[@ACTION='Install']"):
				zipPath = e.attrib['VALUE']
				target = e.attrib['TARGET']

				if discriminators := [e.attrib[attr] for attr in ['PLATFORM', 'BITARCH', 'TYPE', 'VERSION'] if attr in e.attrib]:
					target += f"[{'-'.join(discriminators)}]"

				manifestPath = Path(target, *Path(zipPath).parts[1:]).as_posix()

				if self._zipFS.isdir(zipPath):
					self._manifestfs.makedirs(manifestPath, recreate=True)

				elif self._zipFS.isfile(zipPath):
					if self._manifestfs.exists(manifestPath):
						raise errors.CreateFailed(f"Duplicate file found in manifest (likely due to unimplemented PLATFORM, BITARCH, or VERSION attribute): {manifestPath}.")

					self._manifestfs.makedirs(Path(manifestPath).parent.as_posix(), recreate=True)
					self._manifestfs.writetext(manifestPath, zipPath)

	def __repr__(self) -> str:
		return f"{self.__class__.__name__}({self._file!r})"

	def __str__(self) -> str:
		return f"<{self.__class__.__name__.lower()} {self._file!r}>"

	def close(self) -> None:
		self._zipFS.close()
		self._manifestfs.close()
		super().close()

	def getmeta(self, namespace: str = "standard") -> Mapping[str, object]:
		return self._zipFS.getmeta(namespace)

	def delegate_fs(self) -> ReadZipFS:
		return self._zipFS

	def listdir(self, path: str) -> list[str]:
		self.check()
		return self._manifestfs.listdir(path)

	def getinfo(self, path: str, namespaces: Collection[str] | None = None) -> Info:
		self.check()
		if self._manifestfs.isfile(path):
			return self._zipFS.getinfo(self._manifestfs.readtext(path), namespaces)
		return self._manifestfs.getinfo(path, namespaces)

	def openbin(self, path: str, mode: str = "r", buffering: int = -1, **options: Any) -> BinaryIO:
		self.check()
		if any(elem in mode for elem in 'w+a'):
			raise errors.ResourceReadOnly(path)

		if self._manifestfs.isfile(path):
			return self._zipFS.openbin(self._manifestfs.readtext(path), mode, buffering, **options)
		return self._manifestfs.openbin(path, mode, buffering, **options)

	def makedir(self, path: str, permissions: Permissions | None = None, recreate: bool = False) -> NoReturn:
		self.check()
		raise errors.ResourceReadOnly(path)

	def remove(self, path: str) -> NoReturn:
		self.check()
		raise errors.ResourceReadOnly(path)

	def removedir(self, path: str) -> NoReturn:
		self.check()
		raise errors.ResourceReadOnly(path)

	def setinfo(self, path: str, info: RawInfo) -> NoReturn:
		self.check()
		raise errors.ResourceReadOnly(path)

	def geturl(self, path: str, purpose: str = 'download') -> str:
		if purpose == 'fs' and isinstance(self._file, str):
			quoted_file = url_quote(self._file)
			quoted_path = url_quote(abspath(path))
			return f"dimzip://{quoted_file}!{quoted_path}"
		else:
			raise errors.NoURL(path, purpose)