from typing import BinaryIO

import pytest

from fs import ResourceType
from fs._url_tools import url_quote
from fs.errors import CreateFailed, DirectoryExpected, FileExpected, NoURL, ResourceNotFound
from fs.memoryfs import MemoryFS
from fs.opener import open_fs, registry
from fs.opener.errors import NotWriteable
from fs.osfs import OSFS
from fs.zipfs import WriteZipFS

from fs.dimzipfs import DIMZipFS
from fs.dimzipfs.opener import DIMZipOpener

def _createZipFromData(memoryFS: MemoryFS, name: str) -> BinaryIO:
	zipFilename = f'{name}.zip'
	if not memoryFS.exists(zipFilename):
		with memoryFS.openbin(zipFilename, 'w') as file:
			WriteZipFS(file, temp_fs=OSFS(f'tests/data/{name}'))

	return memoryFS.openbin(zipFilename)


@pytest.fixture(scope='module')
def memoryFS() -> MemoryFS:
	return MemoryFS()

@pytest.fixture(scope='module')
def zipfileOSFS(tmp_path_factory: pytest.TempPathFactory) -> str:
	testZip = 'valid.zip'
	tmp_path = tmp_path_factory.mktemp('data')
	osFS = OSFS(tmp_path.as_posix())
	with osFS.openbin(testZip, 'w') as file:
		WriteZipFS(file, temp_fs=OSFS(f'tests/data/valid'))

	return (tmp_path / testZip).as_posix()

def test_missingManifest(memoryFS: MemoryFS) -> None:
	with pytest.raises(CreateFailed):
		DIMZipFS(_createZipFromData(memoryFS, 'no_manifest'))

def test_badManifest(memoryFS: MemoryFS) -> None:
	with pytest.raises(CreateFailed):
		DIMZipFS(_createZipFromData(memoryFS, 'bad_manifest'))

def test_duplicateFiles(memoryFS: MemoryFS) -> None:
	with pytest.raises(CreateFailed):
		DIMZipFS(_createZipFromData(memoryFS, 'duplicate'))

def test_bitarchFiles(memoryFS: MemoryFS) -> None:
	assert DIMZipFS(_createZipFromData(memoryFS, 'bitarch')).listdir('') == ['Temp[PC-32]', 'Temp[PC-64]']

class TestValidDIMZIP:
	@pytest.fixture(scope="class")
	def zipfile(self, memoryFS: MemoryFS) -> BinaryIO:
		return _createZipFromData(memoryFS, 'valid')

	def test_files(self, zipfile: BinaryIO) -> None:
		dimZipFS = DIMZipFS(zipfile)
		testFile = 'Valid Test Product.txt'
		testFileFull = f"Content/ReadMe's/{testFile}"

		assert dimZipFS.exists(testFileFull)
		assert dimZipFS.isfile(testFileFull)
		assert not dimZipFS.isdir(testFileFull)

		assert dimZipFS.getinfo(testFileFull).name == testFile
		assert dimZipFS.getinfo(testFileFull, ['details']).type == ResourceType.file
		assert dimZipFS.getinfo(testFileFull, ['zip']).get('zip', 'CRC') == 1750160359
		assert dimZipFS.getinfo(testFileFull, ['zip']).get('zip', 'compress_size') == 16

		with dimZipFS.openbin(testFileFull) as f:
			assert f.name == testFileFull
			assert f.read() == b'A Test Product'

		with pytest.raises(DirectoryExpected):
			assert dimZipFS.listdir(testFileFull)

	def test_dirs(self, zipfile: BinaryIO) -> None:
		dimZipFS = DIMZipFS(zipfile)
		testDir = "ReadMe's"
		testDirFull = f"Content/{testDir}"

		assert dimZipFS.exists(testDirFull)
		assert dimZipFS.isdir(testDirFull)
		assert not dimZipFS.isfile(testDirFull)
		
		assert dimZipFS.getinfo('').name == ''
		assert dimZipFS.getinfo(testDirFull).name == testDir
		assert dimZipFS.getinfo(testDirFull, ['details']).type == ResourceType.directory

		assert dimZipFS.listdir('') == ['Content']

		with pytest.raises(FileExpected):
			dimZipFS.openbin('')

		with pytest.raises(FileExpected):
			dimZipFS.openbin(testDirFull)

	def test_nonexistent(self, zipfile: BinaryIO) -> None:
		dimZipFS = DIMZipFS(zipfile)
		testFile = 'Nonexistent'

		assert not dimZipFS.exists(testFile)
		assert not dimZipFS.isfile(testFile)
		assert not dimZipFS.isdir(testFile)

		with pytest.raises(ResourceNotFound):
			dimZipFS.getinfo(testFile)

		with pytest.raises(ResourceNotFound):
			dimZipFS.openbin(testFile)

		with pytest.raises(ResourceNotFound):
			dimZipFS.listdir(testFile)

	def test_getmeta(self, zipfile:BinaryIO) -> None:
		dimZipFS = DIMZipFS(zipfile)

		assert dimZipFS.getmeta() == dimZipFS.delegate_fs().getmeta()

	def test_geturl(self, zipfile: BinaryIO, zipfileOSFS: str) -> None:
		dimZipFS = DIMZipFS(zipfile)
		testFileFull = "Content/ReadMe's/Valid Test Product.txt"

		with pytest.raises(NoURL):
			dimZipFS.geturl(testFileFull, purpose="fs")

		dimZipFS = DIMZipFS(zipfileOSFS)
		assert dimZipFS.geturl(testFileFull, purpose="fs") == f"dimzip://{url_quote(zipfileOSFS)}!/{url_quote(testFileFull)}"
	
def	test_opener(zipfileOSFS: str) -> None:
	registry.install(DIMZipOpener)
	with pytest.raises(NotWriteable):
		open_fs(f"dimzip://{url_quote(zipfileOSFS)}", writeable=True)

	assert open_fs(f"dimzip://{url_quote(zipfileOSFS)}").listdir('') == ['Content']