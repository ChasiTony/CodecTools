#include <stdio.h>
#include <stdlib.h>
#include <memory.h>

typedef unsigned char uint8_t;
typedef int int32_t;

enum ToolMode
{
  REMOVE_A_FRAME=0,
  COPY_A_FRAME=1,
};

void WriteFrame(const uint8_t* pSrc,  const int32_t iSrcWidth, const int32_t iTargetWidth, const int32_t iTargetHeight, 
                FILE* fp)
{
    for (int j=0;j<iTargetHeight;j++)
    {
        fwrite( pSrc+j*iSrcWidth, 1, iTargetWidth, fp );
    }
}

void Processing(int iMode, char* src_yuv, char* dst_yuv, int iWidth, int iHeight, int iPos){
  FILE *fpSrc = fopen(src_yuv, "rb");
  FILE *fpDst = fopen(dst_yuv, "wb");
  
  if (fpSrc==NULL) {
    printf("Open Source file failed!\n");
    return;
  }
  if (fpDst==NULL) {
    printf("Open Target file failed!\n");
    return;
  }
  
  int32_t i, j, k;
  const int32_t iCWidth =iWidth>>1;
  const int32_t iCHeight = iHeight>>1;
  const int32_t iLumaSize = iWidth*iHeight;
  const int32_t iChromaSize = iCWidth*iCHeight;
  uint8_t *pSrcY = (uint8_t *)malloc(iLumaSize);
  uint8_t *pSrcU = (uint8_t *)malloc(iLumaSize);
  uint8_t *pSrcV = (uint8_t *)malloc(iLumaSize);
  
  if (iMode == REMOVE_A_FRAME)
  {
    int iFileLen = 0;
    
    if (fpSrc && !fseek (fpSrc, 0, SEEK_END)) {
      iFileLen = ftell (fpSrc);
      fseek (fpSrc, 0, SEEK_SET);
    }
    
    j=0;
    int iFrameSize = iLumaSize+iChromaSize+iChromaSize;
    int iLeftLength = iFileLen;
    //rewrite each frame
    while( EOF != ftell(fpSrc) && iLeftLength )
    {
      fread( pSrcY, 1, iLumaSize, fpSrc );
      fread( pSrcU, 1, iChromaSize, fpSrc );
      fread( pSrcV, 1, iChromaSize, fpSrc );
      
      if (j!=iPos){
        WriteFrame(pSrcY, iWidth, iWidth, iHeight, fpDst);
        WriteFrame(pSrcU, iWidth>>1, iWidth>>1, iHeight>>1, fpDst);
        WriteFrame(pSrcV, iWidth>>1, iWidth>>1, iHeight>>1, fpDst);
      } else {
        fprintf(stdout, "Skip Frame#%d\n", j);
      }
      
      iLeftLength -= iFrameSize;
      j++;
    }
    
    fclose(fpDst);
    fclose(fpSrc);
  }
  if (iMode == COPY_A_FRAME)
  {
    fprintf(stdout, "Going to Copy Frame#%d\n", iPos);
    int iFileLen = 0;
    
    if (fpSrc && !fseek (fpSrc, 0, SEEK_END)) {
      iFileLen = ftell (fpSrc);
      fseek (fpSrc, 0, SEEK_SET);
    }
    
    j=0;
    int iFrameSize = iLumaSize+iChromaSize+iChromaSize;
    int iLeftLength = iFileLen;
    //rewrite each frame
    while( EOF != ftell(fpSrc) && iLeftLength )
    {
      fread( pSrcY, 1, iLumaSize, fpSrc );
      fread( pSrcU, 1, iChromaSize, fpSrc );
      fread( pSrcV, 1, iChromaSize, fpSrc );
      
      WriteFrame(pSrcY, iWidth, iWidth, iHeight, fpDst);
      WriteFrame(pSrcU, iWidth>>1, iWidth>>1, iHeight>>1, fpDst);
      WriteFrame(pSrcV, iWidth>>1, iWidth>>1, iHeight>>1, fpDst);
      
      if (j==iPos){
        WriteFrame(pSrcY, iWidth, iWidth, iHeight, fpDst);
        WriteFrame(pSrcU, iWidth>>1, iWidth>>1, iHeight>>1, fpDst);
        WriteFrame(pSrcV, iWidth>>1, iWidth>>1, iHeight>>1, fpDst);
        fprintf(stdout, "Copy Frame#%d\n", j);
      }
      
      iLeftLength -= iFrameSize;
      j++;
    }
    
    fclose(fpDst);
    fclose(fpSrc);
  }
  free(pSrcY);
  free(pSrcU);
  free(pSrcV);
}
int main(int argc, char* argv[])
{
  if (argc !=6) {
    printf("usage: mode(0) Src.yuv Dst.yuv iWidth iHeight iPos...");
  }
  
  const int32_t iMode= atoi(argv[1]);
  const int32_t iWidth = atoi(argv[4]);
  const int32_t iHeight = atoi(argv[5]);


  const int32_t iPos = atoi(argv[6]);
  Processing(iMode, argv[2], argv[3], iWidth, iHeight, iPos);
  
  fprintf(stdout, "Finish dealing!\n");
  return 0;
}

